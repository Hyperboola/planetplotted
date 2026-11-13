# Il registro dell'immagine Docker della pipeline
resource "aws_ecr_repository" "pipeline" {
  name                 = "planetplotted"
  image_tag_mutability = "MUTABLE" # il tag "latest" viene aggiornato a ogni pubblicazione

  # Controllo automatico delle vulnerabilità note a ogni pubblicazione
  image_scanning_configuration {
    scan_on_push = true
  }
}

# Tiene solo le ultime 10 immagini: le vecchie occupano spazio e costano
resource "aws_ecr_lifecycle_policy" "pipeline" {
  repository = aws_ecr_repository.pipeline.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Tieni le ultime 10 immagini"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 10
      }
      action = { type = "expire" }
    }]
  })
}

output "ecr_repository_url" {
  description = "Indirizzo del registro, da usare nella CI"
  value       = aws_ecr_repository.pipeline.repository_url
}