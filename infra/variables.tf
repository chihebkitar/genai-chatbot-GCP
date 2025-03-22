variable "project_id" {
  type        = string
  description = "The ID of the GCP project"
}

variable "region" {
  type        = string
  description = "GCP region"
  default     = "us-central1"
}

variable "cluster_name" {
  type        = string
  description = "Name of the GKE cluster"
  default     = "genai-chatbot-cluster"
}

variable "artifact_registry_repo_name" {
  type        = string
  description = "Name of the Artifact Registry repository"
  default     = "genai-chatbot-repo"
}

variable "openai_token" {
  type        = string
  description = "OpenAI Token to store in Secret Manager"
  sensitive   = true
}

variable "pinecone_token" {
  type        = string
  description = "Pinecone Token to store in Secret Manager"
  sensitive   = true
}
