from django.urls import path

from . import views

app_name = 'clips'

urlpatterns = [
    path('', views.feed, {'tab': 'latest'}, name='feed'),
    path('ranking/<str:tab>/', views.feed, name='feed_tab'),
    path('clips/<int:pk>/', views.clip_detail, name='detail'),
    path('clips/<int:pk>/view/', views.clip_view, name='view'),
    path('clips/<int:pk>/report/', views.clip_report, name='report'),
    path('submit/', views.clip_submit, name='submit'),
    path('signup/', views.SignUpView.as_view(), name='signup'),
    path('login/', views.ClipsLoginView.as_view(), name='login'),
    path('logout/', views.ClipsLogoutView.as_view(), name='logout'),
    path('terms/', views.terms, name='terms'),
    path('privacy/', views.privacy, name='privacy'),
    path('robots.txt', views.robots_txt, name='robots'),
    path('sitemap.xml', views.sitemap_xml, name='sitemap'),
]
