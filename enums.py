from enum import Enum, auto

class ChoiceEnum(Enum):
    @classmethod
    def choices(cls):
        return tuple((i.name, i.value) for i in cls)

class ElectionLevel(ChoiceEnum):

    FEDERAL = auto()
    REGIONAL = auto()
    MUNICIPAL = auto()

class ElectionMandateType(ChoiceEnum):

    SINGLE_MANDATE = auto()
    MULTI_MANDATE = auto()
    PARTY_LIST = auto()

class NominatorType(ChoiceEnum):

    PARTY = auto()
    SELF_NOMINATION = auto()
    OTHER = auto()

class DistrictType(ChoiceEnum):

    REGION = auto()
    WHOLE_COUNTRY = auto()
    OKRUG = auto()
    RAYON = auto()

class CommissionType(ChoiceEnum):

    CIK = auto()
    SIK = auto()
    OIK = auto()
    TIK = auto()
    UIK = auto()
    MIK = auto()

class CommissionPositionType(ChoiceEnum):

    HEAD = auto()
    DEPUTY = auto()
    SECRETARY = auto()
    MEMBER = auto()

class CandidateType(ChoiceEnum):

    PARTY = auto()
    PERSON = auto()
    OTHER = auto()



