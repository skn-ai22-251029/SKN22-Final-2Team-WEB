from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def order_list(request):
    return render(request, "orders/list.html")


@login_required
def used_products(request):
    return render(request, "orders/products.html")
