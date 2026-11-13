variable "region" {
  description = "Regione AWS di tutte le risorse"
  type        = string
  default     = "eu-north-1"
}

variable "aws_profile" {
  description = "Profilo della AWS CLI da usare in locale"
  type        = string
  default     = "planetplotted-terraform"
}