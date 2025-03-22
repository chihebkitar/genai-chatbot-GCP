provider "kubernetes" {
  host                   = google_container_cluster.genai_chatbot_cluster.endpoint
  token                  = data.google_client_config.current.access_token
  cluster_ca_certificate = base64decode(google_container_cluster.genai_chatbot_cluster.master_auth[0].cluster_ca_certificate)
}

resource "kubernetes_service_account" "chatbot_k8s_sa" {
  metadata {
    name      = "chatbot-sa"
    namespace = "default"
    annotations = {
      "iam.gke.io/gcp-service-account" = google_service_account.chatbot_sa.email
    }
  }

  # ensure the GKE cluster exists before creating the K8s SA
  depends_on = [google_container_cluster.genai_chatbot_cluster]
}
