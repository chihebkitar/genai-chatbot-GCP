terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 4.53.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
  # For local runs, ensure GOOGLE_APPLICATION_CREDENTIALS is set or use Cloud Shell
}

############################
# 2) Create GKE Cluster (Autopilot)
############################
resource "google_container_cluster" "genai_chatbot_cluster" {
  name             = var.cluster_name
  location         = var.region
  project          = var.project_id
  enable_autopilot = true

}

############################
# 3) Artifact Registry Repository
############################
resource "google_artifact_registry_repository" "genai_repo" {
  project       = var.project_id
  location      = var.region
  repository_id = var.artifact_registry_repo_name
  format        = "DOCKER"
  description   = "Artifact Registry for GENAI Chatbot images"
}

############################
# 4) Secret Manager (Optional)
############################

# -- A) OPENAI_TOKEN Secret
resource "google_secret_manager_secret" "openai_secret" {
  project   = var.project_id
  secret_id = "OPENAI_TOKEN"

  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }
}

resource "google_secret_manager_secret_version" "openai_secret_version" {
  secret      = google_secret_manager_secret.openai_secret.id
  secret_data = var.openai_token
}

# -- B) PINECONE_TOKEN Secret
resource "google_secret_manager_secret" "pinecone_secret" {
  project   = var.project_id
  secret_id = "PINECONE_TOKEN"

  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }
}

resource "google_secret_manager_secret_version" "pinecone_secret_version" {
  secret      = google_secret_manager_secret.pinecone_secret.id
  secret_data = var.pinecone_token
}
