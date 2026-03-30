from django.urls import path
from . import views

urlpatterns = [
    # Auth Routes
    path('signup/', views.signup_view, name='signup_view'),
    path('login/', views.login_view, name='login_view'),
    path('logout/', views.logout_view, name='logout_view'),
    
    # App Routes
    path('', views.operator_view, name='operator_view'),
    path('api/scan/', views.process_scan, name='process_scan'),
    path('marketplace/', views.marketplace_view, name='marketplace_view'),
    path('thread/', views.digital_thread_view, name='digital_thread_view'),
    path('api/verify/<int:item_id>/', views.verify_item, name='verify_item'),
    path('twin/<str:item_id>/', views.digital_twin_detail, name='digital_twin_detail'),
    path('analytics/', views.analytics_dashboard_view, name='analytics_dashboard_view'),
    path('api/group-items/', views.group_items_api, name='group_items_api'),
    path('api/purchase/<str:item_id>/', views.purchase_item_api, name='purchase_item_api'),
    path('analytics/export/', views.export_compliance_csv, name='export_compliance_csv'),
    path('api/add-weight/', views.add_weight_api, name='add_weight_api'),
]