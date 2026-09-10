from cassandra.cluster import Cluster, ExecutionProfile, EXEC_PROFILE_DEFAULT
from cassandra.policies import WhiteListRoundRobinPolicy

DEFAULT_CONTACT_POINT = "127.0.0.1"
DEFAULT_PORT = 9042

def get_cluster(contact_point: str = DEFAULT_CONTACT_POINT, port: int=DEFAULT_PORT) -> Cluster:
    profile = ExecutionProfile(
        load_balancing_policy=WhiteListRoundRobinPolicy([contact_point]),
    )
    return Cluster(
        contact_point=[contact_point],
        port=port,
        execution_profiles={EXEC_PROFILE_DEFAULT: profile},
    )