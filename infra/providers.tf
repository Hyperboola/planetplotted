provider "aws" {
  region  = var.region
  profile = var.aws_profile

  # Etichette aggiunte automaticamente a ogni risorsa creata:
  # nella console si capisce subito cosa appartiene al progetto
  default_tags {
    tags = {
      Project     = "planetplotted"
      Environment = "prod"
      ManagedBy   = "terraform"
    }
  }
}

# Legge il numero dell'account: serve per dare ai bucket un nome unico
data "aws_caller_identity" "current" {}