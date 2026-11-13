# I nomi dei bucket sono unici in tutto il mondo: aggiungiamo il numero dell'account
locals {
  buckets = {
    bronze  = "planetplotted-bronze-${data.aws_caller_identity.current.account_id}"
    renders = "planetplotted-renders-${data.aws_caller_identity.current.account_id}"
  }
}

resource "aws_s3_bucket" "this" {
  for_each = local.buckets
  bucket   = each.value
}

# Nessun accesso pubblico: le immagini arriveranno al sito tramite CloudFront
resource "aws_s3_bucket_public_access_block" "this" {
  for_each                = aws_s3_bucket.this
  bucket                  = each.value.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# File cifrati a riposo, con le chiavi gestite da S3 (gratis)
resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  for_each = aws_s3_bucket.this
  bucket   = each.value.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

output "bucket_names" {
  description = "Nomi dei bucket creati"
  value       = { for k, b in aws_s3_bucket.this : k => b.bucket }
}