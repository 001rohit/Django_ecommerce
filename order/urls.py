from django.urls import path
from . import views

urlpatterns = [    
    path('place_order/', views.place_order, name='place_order'),
    path('payments/', views.payments, name='payments'),
    path('first_checkout/', views.checkout_session, name='first_checkout'),
    path('first_checkout/success/', views.checkout_success, name='checkout_success'),
    path('first_checkout/failure/', views.checkout_failure, name='checkout_failure'),
]