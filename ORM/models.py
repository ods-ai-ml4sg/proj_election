from django.conf import settings
from django.db import models
from django.utils import timezone
from enums import ElectionLevel, ElectionMandateType, NominatorType, DistrictType, CommissionType, CommissionPositionType, CandidateType


class Nominator(models.Model):
    name = models.CharField(max_length=1000)
    superior_nominator = models.ForeignKey("self", on_delete=models.CASCADE,
                                           blank=True, null=True)
    type = models.CharField(max_length=50, choices=NominatorType.choices(),
                                           blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        managed = True
        db_table = 'nominator'


class Region(models.Model):
    name = models.CharField(max_length=200)
    name_eng = models.CharField(max_length=200)

    def __str__(self):
        return self.name

    class Meta:
        managed = True
        db_table = 'region'


class Election(models.Model):
    name = models.CharField(max_length=1000)
    election_level = models.CharField(max_length=50, choices=ElectionLevel.choices(), blank=True, null=True)
    election_mandate_type = models.CharField(max_length=50, choices=ElectionMandateType.choices(), blank=True, null=True)
    mandates = models.IntegerField(blank=True, null=True)
    previous_election = models.ForeignKey("self", on_delete=models.DO_NOTHING,
                                          related_name='next_elections',
                                          blank=True, null=True)
    superior_election = models.ForeignKey("self", on_delete=models.DO_NOTHING,
                                          related_name='child_elections',
                                          blank=True, null=True)
    election_date = models.DateField(blank=False, null=False)
    election_url = models.TextField(blank=False, null=False)


    def __str__(self):
        return self.name

    class Meta:
        managed = True
        db_table = 'election'

        constraints = [
            models.UniqueConstraint(fields=['election_url'], name='unique_election_url'),
        ]


class Commission(models.Model):
    id = models.IntegerField(primary_key=True)
    iz_id = models.BigIntegerField(blank=True, null=True)
    name = models.CharField(max_length=1000)
    commission_type = models.CharField(max_length=10, choices=CommissionType.choices())
    address = models.CharField(max_length=2000,
                             blank=True, null=True) # address data is missing on occasion
    superior_commission = models.ForeignKey("self", on_delete=models.CASCADE,
                                            blank=True, null=True)
    region = models.ForeignKey(Region, on_delete=models.CASCADE,
                               blank=True, null=True)
    phone = models.CharField(max_length=250,
                             blank=True, null=True)
    fax = models.CharField(max_length=250,
                           blank=True, null=True)
    email = models.CharField(max_length=250,
                             blank=True, null=True)
    end_date = models.CharField(max_length=250,
                                blank=True, null=True)
    address_voteroom = models.CharField(max_length=2000,
                                        blank=True, null=True)
    phone_voteroom = models.CharField(max_length=250,
                                      blank=True, null=True)
    lat_ik = models.CharField(max_length=250,
                              blank=True, null=True)
    lon_ik = models.CharField(max_length=250,
                              blank=True, null=True)
    lat_voteroom = models.CharField(max_length=250,
                                    blank=True, null=True)
    lon_voteroom = models.CharField(max_length=250,
                                    blank=True, null=True)
    snapshot_date = models.DateField(blank=False, null=False)

    def __str__(self):
        return self.name

    class Meta:
        managed = True
        db_table = 'commission'


class CommissionMember(models.Model):
    name = models.CharField(max_length=1000)
    position = models.CharField(max_length=50, choices=CommissionPositionType.choices())
    commission = models.ForeignKey(Commission, on_delete=models.CASCADE)
    nominator = models.ForeignKey(Nominator, on_delete=models.CASCADE, null=True)
    snapshot_date = models.DateField(blank=False, null=False)

    def __str__(self):
        return self.name

    class Meta:
        managed = True
        db_table = 'commission_member'


class CommissionProtocol(models.Model):
    commission = models.ForeignKey(Commission, on_delete=models.CASCADE, blank=True, null=True)
    protocol_url = models.TextField()
    election = models.ForeignKey(Election, on_delete=models.CASCADE)
    amount_of_voters = models.IntegerField()
    ballots_received = models.IntegerField()
    ballots_given_out_early = models.IntegerField()
    ballots_given_out_early_at_superior_commission = models.IntegerField()
    ballots_given_out_early_at_uik = models.IntegerField()
    ballots_given_out_early_far_away = models.IntegerField()
    ballots_given_out_at_stations = models.IntegerField()
    ballots_given_out_outside = models.IntegerField()
    ballots_given_out_total = models.IntegerField()
    canceled_ballots = models.IntegerField()
    ballots_found_outside = models.IntegerField()
    ballots_found_at_station = models.IntegerField()
    ballots_found_total = models.IntegerField()
    valid_ballots = models.IntegerField()
    invalid_ballots = models.IntegerField()
    lost_ballots = models.IntegerField()
    appeared_ballots = models.IntegerField()
    election_type = models.TextField()

    class Meta:
        managed = True
        db_table = 'commission_protocol'

        constraints = [
            models.UniqueConstraint(fields=['protocol_url', 'election_type'], name='unique_protocol_url'),
        ]

class District(models.Model):
    name = models.CharField(max_length=1000)
    district_type = models.CharField(max_length=50, choices=DistrictType.choices())

    def __str__(self):
        return self.name

    class Meta:
        managed = True
        db_table = 'district'


class CandidatePerformance(models.Model):

    name = models.CharField(max_length=1000)
    candidate_type = models.CharField(max_length=20, choices=CandidateType.choices(), blank=True, null=True)
    commission = models.ForeignKey(CommissionProtocol, on_delete=models.CASCADE)
    election = models.ForeignKey(Election, on_delete=models.CASCADE)
    nominator = models.ForeignKey(Nominator, on_delete=models.CASCADE, blank=True, null=True)
    candidate_birth_date = models.DateField(blank=True, null=True)
    votes = models.IntegerField()
    election_type = models.TextField()


    def __str__(self):
        return self.name

    class Meta:
        managed = True
        db_table = 'candidate_performance'
