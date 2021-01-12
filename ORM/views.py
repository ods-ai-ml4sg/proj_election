from django.shortcuts import render

from rest_framework import viewsets

import ORM.serializers
import ORM.models

class NominatorViewSet(viewsets.ModelViewSet):
    queryset = ORM.models.Nominator.objects.all()
    serializer_class = ORM.serializers.NominatorSerializer


class RegionViewSet(viewsets.ModelViewSet):
    queryset = ORM.models.Region.objects.all()
    serializer_class = ORM.serializers.RegionSerializer


class ElectionViewSet(viewsets.ModelViewSet):
    queryset = ORM.models.Election.objects.all()
    serializer_class = ORM.serializers.ElectionSerializer


class CommissionViewSet(viewsets.ModelViewSet):
    queryset = ORM.models.Commission.objects.all()
    serializer_class = ORM.serializers.CommissionSerializer


class CommissionMemberViewSet(viewsets.ModelViewSet):
    queryset = ORM.models.CommissionMember.objects.all()
    serializer_class = ORM.serializers.CommissionMemberSerializer


class CommissionProtocolViewSet(viewsets.ModelViewSet):
    queryset = ORM.models.CommissionProtocol.objects.all()
    serializer_class = ORM.serializers.CommissionProtocolSerializer


class DistrictViewSet(viewsets.ModelViewSet):
    queryset = ORM.models.District.objects.all()
    serializer_class = ORM.serializers.DistrictSerializer


class CandidatePerformanceProtocolViewSet(viewsets.ModelViewSet):
    queryset = ORM.models.CandidatePerformance.objects.all()
    serializer_class = ORM.serializers.CandidatePerformanceSerializer
