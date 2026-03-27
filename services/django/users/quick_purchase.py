from __future__ import annotations


def split_legacy_address(address):
    if not address:
        return "", ""

    parts = [part.strip() for part in str(address).split("|", 1)]
    address_main = parts[0] if parts else ""
    address_detail = parts[1] if len(parts) > 1 else ""
    return address_main, address_detail


def split_legacy_payment_method(payment_method):
    normalized = str(payment_method or "").strip()
    if not normalized:
        return "", "", ""

    parts = [part.strip() for part in normalized.split(" / ", 1)]
    provider = parts[0] if parts else ""
    detail = parts[1] if len(parts) > 1 else ""
    masked_number = detail if detail and "*" in detail else ""
    return provider, masked_number, normalized


def build_delivery_info(profile):
    address_main = (getattr(profile, "address_main", "") or "").strip()
    address_detail = (getattr(profile, "address_detail", "") or "").strip()
    if not address_main and not address_detail:
        address_main, address_detail = split_legacy_address(getattr(profile, "address", ""))

    recipient_name = (getattr(profile, "recipient_name", "") or getattr(profile, "nickname", "") or "").strip()
    recipient_phone = (getattr(profile, "phone", "") or "").strip()
    postal_code = (getattr(profile, "postal_code", "") or "").strip()
    delivery_summary = " ".join(part for part in [address_main, address_detail] if part).strip()

    return {
        "recipient_name": recipient_name,
        "recipient_phone": recipient_phone,
        "postal_code": postal_code,
        "address_main": address_main,
        "address_detail": address_detail,
        "delivery_summary": delivery_summary,
        "has_delivery_info": bool(recipient_name and recipient_phone and postal_code and address_main and address_detail),
    }


def build_payment_info(profile):
    payment_summary = (getattr(profile, "payment_method", "") or "").strip()
    card_provider = (getattr(profile, "payment_card_provider", "") or "").strip()
    masked_number = (getattr(profile, "payment_card_masked_number", "") or "").strip()
    payment_token_reference = (getattr(profile, "payment_token_reference", "") or "").strip()

    if not payment_summary:
        legacy_provider, legacy_masked_number, legacy_summary = split_legacy_payment_method(payment_summary)
        payment_summary = legacy_summary
        card_provider = card_provider or legacy_provider
        masked_number = masked_number or legacy_masked_number

    if not payment_summary and card_provider and masked_number:
        payment_summary = f"{card_provider} / {masked_number}"

    if not card_provider or not masked_number:
        legacy_provider, legacy_masked_number, legacy_summary = split_legacy_payment_method(getattr(profile, "payment_method", ""))
        card_provider = card_provider or legacy_provider
        masked_number = masked_number or legacy_masked_number
        payment_summary = payment_summary or legacy_summary

    return {
        "card_provider": card_provider,
        "masked_card_number": masked_number,
        "payment_is_default": bool(getattr(profile, "payment_is_default", True)),
        "payment_token_reference": payment_token_reference,
        "payment_summary": payment_summary,
        "has_payment_method": bool(payment_summary and (card_provider or "페이" in payment_summary or "pay" in payment_summary.lower())),
    }


def serialize_quick_purchase_profile(user):
    profile = getattr(user, "profile", None)
    if profile is None:
        return {
            "has_delivery_info": False,
            "has_payment_method": False,
            "recipient_name": "",
            "recipient_phone": "",
            "postal_code": "",
            "address_main": "",
            "address_detail": "",
            "delivery_summary": "",
            "card_provider": "",
            "masked_card_number": "",
            "payment_summary": "",
            "payment_is_default": True,
            "payment_token_reference": "",
        }

    delivery_info = build_delivery_info(profile)
    payment_info = build_payment_info(profile)
    return {**delivery_info, **payment_info}
