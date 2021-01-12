# basic URL Configurations
from django.urls import include, path
# import routers
from rest_framework import routers

# import everything from views
from .views import *

# define the router
router = routers.DefaultRouter()

# define the router path and viewset to be used
router.register(r'nominators', NominatorViewSet)
router.register(r'regions', RegionViewSet)
router.register(r'elections', ElectionViewSet)
router.register(r'comissions', CommissionViewSet)
router.register(r'commission_members', CommissionMemberViewSet)
router.register(r'commission_protocols', CommissionProtocolViewSet)
router.register(r'district', DistrictViewSet)
router.register(r'candidate_performances', CandidatePerformanceProtocolViewSet)

# specify URL Path for rest_framework
urlpatterns = [
    path('', include(router.urls)),
    path('api-auth/', include('rest_framework.urls'))
]