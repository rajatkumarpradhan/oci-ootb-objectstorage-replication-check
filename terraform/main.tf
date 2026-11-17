# TEMPLATE ONLY - NOT plan/apply validated against a live tenancy.
# Built-in resources: OCI Object Storage source bucket + destination bucket in a
# second region (provider alias) + replication policy. Service-side prerequisites
# not modeled here: IAM policies authorizing the Object Storage service in BOTH
# regions, and tenancy subscription to the destination region.

terraform {
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = ">= 5.0"
    }
  }
}

variable "compartment_id" {
  type        = string
  description = "OCID of the compartment"
}

variable "namespace" {
  type        = string
  description = "Object Storage namespace of the tenancy"
}

provider "oci" {
  alias  = "dest"
  region = "ap-hyderabad-1"
}

# Source bucket. Versioning on the SOURCE is independent of replication:
# OCI replicates the latest version of each object either way.
resource "oci_objectstorage_bucket" "source" {
  compartment_id = var.compartment_id
  namespace      = var.namespace
  name           = "prod-invoices"
  freeform_tags  = { criticality = "prod" }
}

# Destination bucket: must already exist before policy creation, must NOT have
# versioning enabled, and must NOT have retention rules - otherwise OCI rejects
# the replication policy (surfacing as a 403/authorization-style failure).
resource "oci_objectstorage_bucket" "destination" {
  provider       = oci.dest
  compartment_id = var.compartment_id
  namespace      = var.namespace
  name           = "prod-invoices-dr"
  freeform_tags  = { criticality = "dr" }
}

# One replication policy per source bucket. After creation the destination is
# read-only; objects uploaded BEFORE policy creation are NOT replicated.
resource "oci_objectstorage_replication_policy" "this" {
  bucket             = oci_objectstorage_bucket.source.name
  namespace          = var.namespace
  name               = "repl-prod-invoices"
  destination_bucket = oci_objectstorage_bucket.destination.name
  destination_region = "ap-hyderabad-1"
}
