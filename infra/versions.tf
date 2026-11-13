terraform {
  required_version = ">= 1.17"

  # Lo stato e la cronologia vivono su HCP Terraform
  cloud {
    organization = "planetplotted"
    workspaces {
      name = "planetplotted-prod"
    }
  }

  # Il "provider" è il plugin che sa parlare con AWS
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}