from rest_framework import serializers
import ORM.models

class NominatorSerializer(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        model = ORM.models.Nominator


class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        model = ORM.models.Region


class ElectionSerializer(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        model = ORM.models.Election


class CommissionSerializer(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        model = ORM.models.Commission


class CommissionMemberSerializer(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        model = ORM.models.CommissionMember


class CommissionProtocolSerializer(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        model = ORM.models.CommissionProtocol


class DistrictSerializer(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        model = ORM.models.District


class CandidatePerformanceSerializer(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        model = ORM.models.CandidatePerformance
