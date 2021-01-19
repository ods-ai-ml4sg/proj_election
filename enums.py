from enum import Enum, auto

class ChoiceEnum(Enum):
    @classmethod
    def choices(cls):
        return tuple((i.name, i.value) for i in cls)

    @classmethod
    def names(cls):
        return [n.name for n in cls]

class ElectionLevel(ChoiceEnum):

    FEDERAL = auto()
    REGIONAL = auto()
    MUNICIPAL = auto()

class ElectionMandateNumberType(ChoiceEnum):

    SINGLE_MANDATE = auto()
    MULTI_MANDATE = auto()
    NO_MANDATES = auto() # referendums

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

class CandidateListType(ChoiceEnum):
    '''
    is there a single list of candidate across all uiks in elections; or different lists for different territories?
    '''

    COMMON = auto()
    SPECIFIC = auto()

class ElectionsByCandidateListType(ChoiceEnum):

    COMMON = auto()
    SPECIFIC = auto()
    MIXED = auto()


