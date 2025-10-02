import tarfile, json, hashlib, io
from cli.export_bundle import build_bundle, RoleRecord, PolicyRecord, FeatureFlagRecord

def test_export_bundle_integrity_real():
    roles = [RoleRecord(role_id="tenant_admin", permissions=["*"]), RoleRecord(role_id="analyst", permissions=["read"]) ]
    policies = [PolicyRecord(policy_id="p1", version=1, effect="ALLOW"), PolicyRecord(policy_id="p1", version=2, effect="DENY")]
    flags = [FeatureFlagRecord(flag_key="beta_mode", status="enabled")]
    blob = build_bundle(roles, policies, flags)
    # Open tar.gz in memory and read files
    bio = io.BytesIO(blob)
    with tarfile.open(fileobj=bio, mode="r:gz") as tf:
        members = {}
        for m in tf.getmembers():
            if not m.isfile():
                continue
            extracted = tf.extractfile(m)
            if not extracted:  # skip if None
                continue
            members[m.name] = extracted.read().decode()
    assert {"roles.json", "policies.json", "feature_flags.json", "metadata.json"}.issubset(members.keys())
    concat = "".join(members[k] for k in sorted([k for k in members.keys() if k != "metadata.json"]))
    digest = hashlib.sha256(concat.encode()).hexdigest()
    metadata = json.loads(members["metadata.json"])
    assert metadata["sha256"] == digest, "Bundle hash mismatch"
