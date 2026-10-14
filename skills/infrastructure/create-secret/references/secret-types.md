# Secret Types Reference

## SecretFile

Stores file-based secrets: certificates, PEM files, config files.

```yaml
secret:
  identifier: ssl_cert
  name: SSL Certificate
  description: Production SSL certificate
  type: SecretFile
  spec:
    secretManagerIdentifier: harnessSecretManager
```

## SSHKey

SSH credentials for remote server access.

### Key Reference (recommended)

```yaml
secret:
  identifier: ssh_deploy_key
  name: SSH Deploy Key
  type: SSHKey
  spec:
    auth:
      type: SSH
      spec:
        credentialType: KeyReference
        spec:
          userName: deploy
          key: ssh_private_key_ref
          encryptedPassphrase: ssh_passphrase  # optional
    port: 22
```

### Key Path (on delegate)

```yaml
secret:
  identifier: ssh_key_path
  name: SSH Key Path
  type: SSHKey
  spec:
    auth:
      type: SSH
      spec:
        credentialType: KeyPath
        spec:
          userName: ubuntu
          keyPath: /home/harness/.ssh/id_rsa
    port: 22
```

### Password-based

```yaml
secret:
  identifier: ssh_password
  name: SSH Password
  type: SSHKey
  spec:
    auth:
      type: SSH
      spec:
        credentialType: Password
        spec:
          userName: admin
          password: ssh_password_secret
    port: 22
```

## WinRmCredentials

Windows Remote Management credentials.

### NTLM

```yaml
secret:
  identifier: winrm_creds
  name: WinRM Credentials
  type: WinRmCredentials
  spec:
    auth:
      type: NTLM
      spec:
        username: Administrator
        password: winrm_password
        domain: MYDOMAIN
    port: 5986
    useSSL: true
```

### Kerberos

```yaml
secret:
  identifier: winrm_kerberos
  name: WinRM Kerberos
  type: WinRmCredentials
  spec:
    auth:
      type: Kerberos
      spec:
        principal: admin@MYDOMAIN.COM
        realm: MYDOMAIN.COM
        tgtGenerationMethod:
          type: KeyTabFilePath
          spec:
            keyTabFilePath: /etc/krb5.keytab
    port: 5986
    useSSL: true
```

## Secret Manager References

| Manager | `secretManagerIdentifier` | `valueType` |
|---------|--------------------------|-------------|
| Harness Built-in | `harnessSecretManager` | `Inline` |
| HashiCorp Vault | `<vault_connector_id>` | `Reference` |
| AWS Secrets Manager | `<aws_sm_connector_id>` | `Reference` |
| Azure Key Vault | `<akv_connector_id>` | `Reference` |
| GCP Secret Manager | `<gcp_sm_connector_id>` | `Reference` |

For external managers, `value` is the secret path/name in the external store:

```yaml
# Vault example
spec:
  secretManagerIdentifier: hashicorp_vault
  valueType: Reference
  value: secret/data/myapp/api-key#key

# AWS Secrets Manager example
spec:
  secretManagerIdentifier: aws_secrets_manager
  valueType: Reference
  value: my-secret-name
```
