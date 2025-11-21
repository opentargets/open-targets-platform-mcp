"""Tool for providing example GraphQL queries for the OpenTargets API."""

from otar_mcp.server import mcp

EXAMPLE_QUERIES = {
    "informationForTargetByEnsemblId": """
        query informationForTargetByEnsemblId {
            target(ensemblId: "ENSG00000169083") {
                id
                approvedSymbol
                tractability {
                    modality
                    label
                    value
                }
                safetyLiabilities {
                    event
                    eventId
                    biosamples {
                        cellFormat
                        cellLabel
                        tissueLabel
                        tissueId
                    }
                    effects {
                        dosing
                        direction
                    }
                    studies {
                        name
                        type
                        description
                    }
                    datasource
                    literature
                }
            }
        }
    """,
    "drugsForTargetByEnsemblId": """
        query geneAssociatedDrugs {
            target(ensemblId: "ENSG00000159640") {
                id
                pharmacogenomics {
                    isDirectTarget
                    target {
                        approvedName
                    }
                    drugs {
                        drug {
                        id
                        name
                        mechanismsOfAction {
                            rows {
                            targets {
                                approvedName
                            }
                            }
                            uniqueTargetTypes
                            uniqueActionTypes
                        }
                        isApproved
                        }
                    }
                }
            }
        }
    """,
    "associatedDiseasesForTargetByEnsemblId": """
        query associatedDiseasesForTargetByEnsemblId {
            target(ensemblId: "ENSG00000127318") {
                id
                approvedSymbol
                associatedDiseases {
                    count
                    rows {
                        disease {
                            id
                            name
                        }
                        datasourceScores {
                            id
                            score
                        }
                    }
                }
            }
        }
    """,
    "informationForDiseaseByEFOId": """
        query informationForDiseaseByEFOId {
            disease(efoId: "EFO_0000222") {
                id
                name
                phenotypes {
                    rows {
                        phenotypeHPO {
                            id
                            name
                            description
                            namespace
                        }
                        phenotypeEFO {
                            id
                            name
                        }
                        evidence {
                            aspect
                            bioCuration
                            diseaseFromSourceId
                            diseaseFromSource
                            evidenceType
                            frequency
                            frequencyHPO {
                                name
                                id
                            }
                            qualifierNot
                            onset {
                                name
                                id
                            }
                            modifiers {
                                name
                                id
                            }
                            references
                            sex
                            resource
                        }
                    }
                }
            }
        }
    """,
    "knownDrugsForDiseaseByEFOId": """
        query knownDrugsForDiseaseByEFOId {
            disease(efoId: "EFO_0004705") {
                id
                name
                knownDrugs {
                    count
                    uniqueTargets
                    uniqueDrugs
                    rows {
                        drugId
                        drugType
                        prefName
                        targetId
                        targetClass
                        approvedSymbol
                        mechanismOfAction
                        phase
                        status
                        diseaseId
                        drug {
                            id
                            name
                            maximumClinicalTrialPhase
                            description
                            synonyms
                        }
                        target {
                            id
                            approvedSymbol
                            approvedName
                        }
                    }
                }
            }
        }
    """,
    "associatedTargetsForDiseaseByEFOId": """
        query associatedTargets {
            disease(efoId: "EFO_0000349") {
                id
                name
                associatedTargets {
                    count
                    rows {
                        target {
                            id
                            approvedSymbol
                        }
                        score
                    }
                }
            }
        }
    """,
    "informationForDrugByChemblId": """
        query informationForDrugByChemblId {
            drug(chemblId: "CHEMBL25") {
                name
                id
                yearOfFirstApproval
                tradeNames
                isApproved
                hasBeenWithdrawn
                blackBoxWarning
                drugType
                approvedIndications
                mechanismsOfAction {
                    uniqueTargetTypes
                    uniqueActionTypes
                }
                linkedTargets {
                    rows {
                        id
                        approvedName
                        pathways {
                            pathwayId
                            pathway
                            topLevelTerm
                        }
                    }
                }
            }
        }
    """,
}


@mcp.tool()
def get_open_targets_query_examples() -> dict:
    """Get example GraphQL queries for the Open Targets API.

    Returns a dictionary of named example queries that can be used with the
    query_open_targets_graphql tool. These examples demonstrate common use cases
    for retrieving data about targets, diseases, drugs, and their associations.
    """
    return EXAMPLE_QUERIES
