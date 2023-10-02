variable "name" {
  description = "Name Used for EKS Cluster"
  type        = string
  default     = "fedml-edge-server"
}

variable "node_group_disk_size" {
  description = "Disk size in GiB for nodes. Defaults to `20`. Only valid when `use_custom_launch_template` = `false`"
  type        = number
  default     = 100
}