#### Data sources (to lookup your cluster & caller identity) ####
data "google_client_config" "current" {}


#### 3.5.1 Create dedicated GCP Service Account ####
resource "google_service_account" "chatbot_sa" {
  project      = var.project_id
  account_id   = "genai-chatbot-wi-sa"
  display_name = "Workload Identity SA for GenAI Chatbot"
}

#### 3.5.2 Grant minimal Secret Manager access ####
resource "google_project_iam_member" "chatbot_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.chatbot_sa.email}"

  depends_on = [
    google_secret_manager_secret_version.openai_secret_version,
    google_secret_manager_secret_version.pinecone_secret_version,
  ]
}
