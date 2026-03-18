# shared/utils/k8s_client.py
"""
Shared Kubernetes client wrapper.
Supervisor uses it to read pods/logs.
Resolver uses it to restart/scale workloads.
Auto-detects local kubeconfig vs in-cluster config.
"""
import os
from kubernetes import client, config
from shared.utils.logger import get_logger

logger = get_logger("k8s_client")


def get_k8s_clients():
    """
    Returns (CoreV1Api, AppsV1Api) tuple.
    Loads in-cluster config when running inside Kubernetes,
    otherwise loads local kubeconfig file.
    """
    try:
        if os.getenv("KUBERNETES_SERVICE_HOST"):
            config.load_incluster_config()
            logger.info("Loaded in-cluster Kubernetes config")
        else:
            config.load_kube_config()
            logger.info("Loaded local kubeconfig")
    except Exception as e:
        logger.error(f"Failed to load Kubernetes config: {e}")
        raise

    return client.CoreV1Api(), client.AppsV1Api()


def get_pod_logs(
    core_v1: client.CoreV1Api,
    namespace: str,
    pod_name: str,
    tail_lines: int = 100,
) -> str:
    """
    Fetches the last N log lines from a running pod.
    Returns an error string (never raises) so the pipeline continues.
    """
    try:
        return core_v1.read_namespaced_pod_log(
            name=pod_name,
            namespace=namespace,
            tail_lines=tail_lines,
        )
    except Exception as e:
        logger.warning(f"Could not fetch logs for {namespace}/{pod_name}: {e}")
        return f"LOG_FETCH_ERROR: {e}"
