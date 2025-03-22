output "gke_cluster_name" {
  description = "Name of the created GKE cluster"
  value       = google_container_cluster.genai_chatbot_cluster.name
}

output "artifact_registry_repo" {
  description = "Artifact Registry repository URL"
  value       = google_artifact_registry_repository.genai_repo.id
}
