variable "github_repository" {
  description = "Repository GitHub autorizzato a usare il ruolo della CI"
  type        = string
  default     = "Hyperboola/planetplotted"
}

# AWS si fida dei "documenti d'identità" emessi da GitHub Actions
resource "aws_iam_openid_connect_provider" "github" {
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
}

# Chi può usare il ruolo: solo questo repository, solo dal branch main
data "aws_iam_policy_document" "github_trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_repository}:ref:refs/heads/main"]
    }
  }
}

resource "aws_iam_role" "github_actions" {
  name               = "planetplotted-github-actions"
  description        = "Ruolo della CI di GitHub: pubblica l'immagine su ECR"
  assume_role_policy = data.aws_iam_policy_document.github_trust.json
}

# Cosa può fare il ruolo: solo pubblicare immagini nel nostro registro
data "aws_iam_policy_document" "github_ecr_push" {
  statement {
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"] # questa azione non si può limitare a un registro
  }
  statement {
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:BatchGetImage",
      "ecr:GetDownloadUrlForLayer",
      "ecr:InitiateLayerUpload",
      "ecr:UploadLayerPart",
      "ecr:CompleteLayerUpload",
      "ecr:PutImage",
    ]
    resources = [aws_ecr_repository.pipeline.arn]
  }
}

resource "aws_iam_role_policy" "github_ecr_push" {
  name   = "ecr-push"
  role   = aws_iam_role.github_actions.id
  policy = data.aws_iam_policy_document.github_ecr_push.json
}

output "github_actions_role_arn" {
  description = "Ruolo da indicare nel workflow di GitHub"
  value       = aws_iam_role.github_actions.arn
}