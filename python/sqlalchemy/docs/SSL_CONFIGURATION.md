# SSL/TLS Configuration

Aurora DSQL requires TLS for all connections. Plaintext connections are not supported. Enabling certificate verification protects against on-path and impersonation attacks.

`create_dsql_engine` defaults to:
- `sslmode="verify-full"` - verifies the server certificate and hostname
- `sslrootcert="system"` - uses the default certificate authority (CA) trust defined by libpq’s TLS backend

## How certificate trust works

When using the `psycopg` or `psycopg2` drivers, TLS verification is performed by libpq.

`sslrootcert="system"` means the driver should use the CAs trusted by the TLS backend which libpq uses (typically OpenSSL).

If the Amazon Root CA is already present in that trust store, no additional configuration is required. If it is not present, certificate verification will fail unless the trust store is extended or an explicit CA bundle is provided.

## Extend the system trust store (recommended)

The preferred approach is to add the Amazon Root CA to the trust store used by your TLS backend. How this is done depends on your platform and OpenSSL installation (for example, updating the system CA bundle or adding a custom CA via your distribution’s tooling).

Once the CA is trusted, the default configuration uses `sslrootcert="system"` and works unchanged, using the most secure connection method:

```python
engine = create_dsql_engine(
    host="<CLUSTER_ENDPOINT>",
    user="<CLUSTER_USER>",
)
```

## Change trust store with `SSL_CERT_FILE`

If you cannot modify the system trust store (for example, in CI or restricted environments), you may point OpenSSL at a CA bundle explicitly:

```bash
wget -O ~/AmazonRootCA1.pem https://www.amazontrust.com/repository/AmazonRootCA1.pem
export SSL_CERT_FILE="$HOME/AmazonRootCA1.pem"
```

With `SSL_CERT_FILE` set, `sslrootcert="system"` will succeed without code changes.

## Provide `sslrootcert` explicitly

You may also pass a CA bundle path directly in code:

```python
engine = create_dsql_engine(
    host="<CLUSTER_ENDPOINT>",
    user="<CLUSTER_USER>",
    sslrootcert="/path/to/AmazonRootCA1.pem",
)
```

This approach is deterministic and fully supported, but less flexible across deployment environments.

## Use `sslmode=require` (not recommended)

You may force encryption without verification:

```python
engine = create_dsql_engine(
    host="<CLUSTER_ENDPOINT>",
    user="<CLUSTER_USER>",
    sslmode="require",
)
```

This encrypts traffic, but disables certificate and hostname verification. It is not recommended for production use, and should only be used for diagnostics or controlled environments.

## Additional resources

See the [PostgreSQL SSL documentation](https://www.postgresql.org/docs/current/libpq-ssl.html#LIBQ-SSL-CERTIFICATES) and [Configuring SSL/TLS certificates for Aurora DSQL connections](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/configure-root-certificates.html) for more information.
