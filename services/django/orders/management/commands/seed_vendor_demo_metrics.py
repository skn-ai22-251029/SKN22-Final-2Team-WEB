import random
import re
import uuid
from collections import Counter
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from orders.models import Order, OrderItem, UserInteraction
from products.models import Product
from users.models import User, UserProfile

PAYMENT_METHOD_CHOICES = (
    "우리카드 1234 / 일시불",
    "카카오페이 / 일시불",
    "네이버페이 / 일시불",
)
BASE_SHIPPING_FEE = 3000
FREE_SHIPPING_THRESHOLD = 30000


def _slugify_label(value):
    return re.sub(r"[^a-z0-9]+", "-", str(value or "").strip().lower()).strip("-") or "vendor"


class Command(BaseCommand):
    help = "Seed demo interactions and orders for a vendor dashboard/analytics view."

    def add_arguments(self, parser):
        parser.add_argument("--brand-name", default="오리젠", help="대상 브랜드명")
        parser.add_argument("--sessions", type=int, default=300, help="생성할 세션 수")
        parser.add_argument("--days", type=int, default=30, help="최근 며칠 범위로 분산할지")
        parser.add_argument("--seed", type=int, default=20260409, help="난수 시드")
        parser.add_argument(
            "--user-pool-size",
            type=int,
            default=0,
            help="재사용할 데모 유저 수 (0이면 세션 수 기반 자동 계산)",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        brand_name = (options["brand_name"] or "").strip()
        sessions = int(options["sessions"] or 0)
        days = int(options["days"] or 0)
        seed = int(options["seed"] or 0)
        user_pool_size = int(options["user_pool_size"] or 0)

        if not brand_name:
            raise CommandError("brand_name is required.")
        if sessions <= 0:
            raise CommandError("sessions must be greater than 0.")
        if days <= 0:
            raise CommandError("days must be greater than 0.")

        products = list(
            Product.objects.filter(brand_name=brand_name).order_by("-review_count", "-rating", "goods_name")[:12]
        )
        if not products:
            raise CommandError(f"No products found for brand '{brand_name}'.")

        rng = random.Random(seed)
        demo_users = self._ensure_demo_users(
            brand_name=brand_name,
            desired_count=user_pool_size or max(12, min(60, sessions // 8 or 1)),
        )
        session_breakdown = self._build_session_breakdown(sessions)
        order_status_counts = self._build_order_status_counts(sessions)

        interaction_counter = Counter()
        order_counter = Counter()

        for session_type, count in session_breakdown.items():
            for _ in range(count):
                created_at = self._pick_created_at(rng, days)
                session_id = uuid.uuid4()
                user = rng.choice(demo_users)
                recommended_products = self._pick_recommendation_products(products, rng)
                target_product = rng.choice(recommended_products)

                for product in recommended_products:
                    self._create_interaction(
                        user=user,
                        product=product,
                        interaction_type="impression",
                        created_at=created_at,
                        session_id=session_id,
                    )
                    interaction_counter["impression"] += 1

                if session_type in {"detail", "cart", "checkout", "purchase"}:
                    self._create_interaction(
                        user=user,
                        product=target_product,
                        interaction_type="click",
                        created_at=created_at,
                        session_id=session_id,
                    )
                    self._create_interaction(
                        user=user,
                        product=target_product,
                        interaction_type="detail_view",
                        created_at=created_at,
                        session_id=session_id,
                    )
                    interaction_counter["click"] += 1
                    interaction_counter["detail_view"] += 1

                if session_type in {"cart", "checkout", "purchase"}:
                    quantity = rng.randint(1, 2)
                    self._create_interaction(
                        user=user,
                        product=target_product,
                        interaction_type="cart",
                        created_at=created_at,
                        session_id=session_id,
                        weight=quantity,
                    )
                    interaction_counter["cart"] += 1
                    if rng.random() < 0.22:
                        self._create_interaction(
                            user=user,
                            product=target_product,
                            interaction_type="wishlist",
                            created_at=created_at,
                            session_id=session_id,
                        )
                        interaction_counter["wishlist"] += 1

                if session_type in {"checkout", "purchase"}:
                    quantity = rng.randint(1, 2)
                    self._create_interaction(
                        user=user,
                        product=target_product,
                        interaction_type="checkout_start",
                        created_at=created_at,
                        session_id=session_id,
                        weight=quantity,
                    )
                    interaction_counter["checkout_start"] += 1

                if session_type == "purchase":
                    order = self._create_order(
                        user=user,
                        line_items=self._build_line_items(recommended_products, target_product, rng),
                        status="completed",
                        created_at=created_at,
                        rng=rng,
                    )
                    order_counter[order.status] += 1
                    for item in order.items.select_related("product").all():
                        interaction_counter["purchase"] += 1

        for status_code, count in order_status_counts.items():
            for _ in range(count):
                created_at = self._pick_created_at(rng, days, prefer_today=True)
                user = rng.choice(demo_users)
                target_product = rng.choice(products)
                order = self._create_order(
                    user=user,
                    line_items=[(target_product, rng.randint(1, 2))],
                    status=status_code,
                    created_at=created_at,
                    rng=rng,
                )
                order_counter[order.status] += 1
                if status_code != "cancelled":
                    for item in order.items.select_related("product").all():
                        interaction_counter["purchase"] += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded vendor demo metrics for {brand_name}: "
                f"sessions={sessions}, users={len(demo_users)}, "
                f"interactions={sum(interaction_counter.values())}, orders={sum(order_counter.values())}"
            )
        )
        for key in (
            "impression",
            "click",
            "detail_view",
            "wishlist",
            "cart",
            "checkout_start",
            "purchase",
        ):
            self.stdout.write(f"- {key}: {interaction_counter.get(key, 0)}")
        for status_code in ("pending", "completed", "cancelled"):
            self.stdout.write(f"- order:{status_code}: {order_counter.get(status_code, 0)}")

    def _build_session_breakdown(self, sessions):
        view_only = int(sessions * 0.40)
        detail_only = int(sessions * 0.30)
        cart_only = int(sessions * 0.20)
        checkout_only = int(sessions * 0.07)
        purchase = max(sessions - view_only - detail_only - cart_only - checkout_only, 0)
        if sessions >= 10 and purchase == 0:
            purchase = 1
            view_only = max(view_only - 1, 0)
        return {
            "view": view_only,
            "detail": detail_only,
            "cart": cart_only,
            "checkout": checkout_only,
            "purchase": purchase,
        }

    def _build_order_status_counts(self, sessions):
        pending = max(1 if sessions >= 10 else 0, round(sessions * 0.05))
        cancelled = max(1 if sessions >= 10 else 0, round(sessions * 0.015))
        return {
            "pending": pending,
            "cancelled": cancelled,
        }

    def _ensure_demo_users(self, *, brand_name, desired_count):
        users = []
        brand_slug = _slugify_label(brand_name)
        for index in range(desired_count):
            email = f"seed-{brand_slug}-{index + 1:03d}@tailtalk.local"
            user = User.objects.filter(email=email).first()
            if user is None:
                user = User.objects.create_user(email=email)
            UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    "nickname": f"{brand_name}데모{index + 1}",
                    "recipient_name": f"{brand_name} 데모고객 {index + 1}",
                    "postal_code": "06123",
                    "address_main": "서울 강남구 테일톡로 1",
                    "address_detail": f"{index + 1}층 {index + 101}호",
                    "address": f"서울 강남구 테일톡로 1 | {index + 1}층 {index + 101}호",
                    "phone": f"010{index + 1000:04d}{index + 2000:04d}",
                    "payment_method": PAYMENT_METHOD_CHOICES[index % len(PAYMENT_METHOD_CHOICES)],
                },
            )
            users.append(user)
        return users

    def _pick_recommendation_products(self, products, rng):
        lower_bound = 1 if len(products) < 3 else 3
        recommendation_count = min(len(products), rng.randint(lower_bound, min(5, len(products))))
        return rng.sample(products, recommendation_count)

    def _pick_created_at(self, rng, days, prefer_today=False):
        now = timezone.now()
        if days <= 1:
            day_offset = 0
        elif prefer_today or rng.random() < 0.30:
            day_offset = 0
        elif days <= 7 or rng.random() < 0.70:
            day_offset = rng.randint(1, min(days - 1, 6))
        else:
            day_offset = rng.randint(7, days - 1)

        hour = rng.randint(8, 22)
        minute = rng.randint(0, 59)
        second = rng.randint(0, 59)
        created_at = (now - timedelta(days=day_offset)).replace(
            hour=hour,
            minute=minute,
            second=second,
            microsecond=0,
        )
        if created_at > now:
            return now
        return created_at

    def _create_interaction(self, *, user, product, interaction_type, created_at, session_id=None, weight=1):
        interaction = UserInteraction.objects.create(
            user=user,
            product=product,
            session_id=session_id,
            interaction_type=interaction_type,
            weight=max(int(weight or 1), 1),
        )
        UserInteraction.objects.filter(pk=interaction.pk).update(created_at=created_at)
        interaction.created_at = created_at
        return interaction

    def _build_line_items(self, recommended_products, target_product, rng):
        line_items = [(target_product, rng.randint(1, 2))]
        if len(recommended_products) > 1 and rng.random() < 0.35:
            extra_product = rng.choice([product for product in recommended_products if product.pk != target_product.pk])
            line_items.append((extra_product, 1))
        return line_items

    def _create_order(self, *, user, line_items, status, created_at, rng):
        product_total = sum(product.price * quantity for product, quantity in line_items)
        shipping_fee = 0 if product_total >= FREE_SHIPPING_THRESHOLD else BASE_SHIPPING_FEE
        payment_method = rng.choice(PAYMENT_METHOD_CHOICES)
        profile = getattr(user, "profile", None)
        recipient_name = (getattr(profile, "recipient_name", "") or getattr(profile, "nickname", "") or user.email).strip()
        recipient_phone = (getattr(profile, "phone", "") or "01012341234").strip()
        delivery_address = (getattr(profile, "address", "") or "서울 강남구 테일톡로 1 | 101동 1203호").strip()

        order = Order.objects.create(
            user=user,
            recipient_name=recipient_name,
            recipient_phone=recipient_phone,
            delivery_address=delivery_address,
            delivery_message="시연용 자동 생성 주문",
            payment_method=payment_method,
            applied_coupon_id="none",
            product_total=product_total,
            coupon_discount=0,
            mileage_discount=0,
            shipping_fee=shipping_fee,
            total_price=product_total + shipping_fee,
            status=status,
        )
        Order.objects.filter(pk=order.pk).update(created_at=created_at)

        order_items = [
            OrderItem(order=order, product=product, quantity=quantity, price_at_order=product.price)
            for product, quantity in line_items
        ]
        OrderItem.objects.bulk_create(order_items)

        if status != "cancelled":
            for product, quantity in line_items:
                self._create_interaction(
                    user=user,
                    product=product,
                    interaction_type="purchase",
                    created_at=created_at,
                    session_id=uuid.uuid4(),
                    weight=max(int(quantity or 1), 1),
                )

        return Order.objects.prefetch_related("items__product").get(pk=order.pk)
