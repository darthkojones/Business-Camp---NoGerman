from typing import List
from schemas import ClusterSchema
from mock_data import MOCK_CLUSTERS

def generate_clusters() -> List[ClusterSchema]:
    """
    Generates product clusters based on shared properties.
    Presently, this returns mocked data, but will eventually
    contain the concrete clustering logic.
    """
    return MOCK_CLUSTERS
