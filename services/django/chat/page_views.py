from .pages.context_builders import build_catalog_menu_sections as _build_catalog_menu_context
from .pages.context_builders import build_quick_order_profile_context as _build_quick_order_profile_context
from .pages.context_builders import display_product_name as _display_product_name
from .pages.context_builders import format_price as _format_price
from .pages.context_builders import preview_member_pets as _preview_member_pets
from .pages.context_builders import preview_session_threads as _preview_session_threads
from .pages.context_builders import preview_sessions as _preview_sessions
from .pages.context_builders import serialize_cart_product as _serialize_cart_product
from .pages.context_builders import serialize_future_pet as _serialize_future_pet
from .pages.context_builders import serialize_pet as _serialize_pet
from .pages.context_builders import serialize_recommended_product as _serialize_recommended_product
from .pages.context_builders import single_product_queryset as _single_product_queryset
from .pages.context_builders import sort_member_pets as _sort_member_pets
from .pages import views as page_view_impl


def chat_view(request):
    return page_view_impl.chat_view(request)


__all__ = [
    "chat_view",
    "_build_catalog_menu_context",
    "_build_quick_order_profile_context",
    "_display_product_name",
    "_format_price",
    "_preview_member_pets",
    "_preview_session_threads",
    "_preview_sessions",
    "_serialize_cart_product",
    "_serialize_future_pet",
    "_serialize_pet",
    "_serialize_recommended_product",
    "_single_product_queryset",
    "_sort_member_pets",
]
