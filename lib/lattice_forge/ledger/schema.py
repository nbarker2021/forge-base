SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS object_registry (
  object_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  kind TEXT NOT NULL,
  rank INTEGER,
  dimension INTEGER,
  family TEXT,
  is_terminal INTEGER DEFAULT 0,
  metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS exact_vectors (
  vector_id TEXT PRIMARY KEY,
  object_id TEXT NOT NULL,
  coordinates_json TEXT NOT NULL,
  norm_json TEXT,
  orbit_label TEXT,
  hash TEXT NOT NULL,
  FOREIGN KEY(object_id) REFERENCES object_registry(object_id)
);

CREATE TABLE IF NOT EXISTS gram_forms (
  gram_id TEXT PRIMARY KEY,
  object_id TEXT NOT NULL,
  matrix_json TEXT NOT NULL,
  determinant_json TEXT,
  scale_convention TEXT,
  hash TEXT NOT NULL,
  FOREIGN KEY(object_id) REFERENCES object_registry(object_id)
);

CREATE TABLE IF NOT EXISTS morphism_registry (
  morphism_id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL,
  target_id TEXT NOT NULL,
  morphism_type TEXT NOT NULL,
  matrix_json TEXT,
  conditions_json TEXT NOT NULL DEFAULT '{}',
  invariant_delta_json TEXT NOT NULL DEFAULT '{}',
  metadata_json TEXT NOT NULL DEFAULT '{}',
  hash TEXT NOT NULL,
  FOREIGN KEY(source_id) REFERENCES object_registry(object_id),
  FOREIGN KEY(target_id) REFERENCES object_registry(object_id)
);

CREATE TABLE IF NOT EXISTS involution_registry (
  involution_id TEXT PRIMARY KEY,
  object_id TEXT NOT NULL,
  name TEXT NOT NULL,
  fixed_structure_id TEXT,
  action_json TEXT NOT NULL DEFAULT '{}',
  metadata_json TEXT NOT NULL DEFAULT '{}',
  hash TEXT NOT NULL,
  FOREIGN KEY(object_id) REFERENCES object_registry(object_id)
);


CREATE TABLE IF NOT EXISTS convolution_registry (
  convolution_id TEXT PRIMARY KEY,
  object_id TEXT NOT NULL,
  name TEXT NOT NULL,
  domain_json TEXT NOT NULL DEFAULT '{}',
  operation_json TEXT NOT NULL DEFAULT '{}',
  metadata_json TEXT NOT NULL DEFAULT '{}',
  hash TEXT NOT NULL,
  FOREIGN KEY(object_id) REFERENCES object_registry(object_id)
);

CREATE TABLE IF NOT EXISTS admissibility_edges (
  edge_id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL,
  target_id TEXT NOT NULL,
  via_morphism_id TEXT,
  status TEXT NOT NULL,        -- legal, forbidden, conditional
  condition_json TEXT NOT NULL DEFAULT '{}',
  obstruction_json TEXT NOT NULL DEFAULT '{}',
  hash TEXT NOT NULL,
  FOREIGN KEY(source_id) REFERENCES object_registry(object_id),
  FOREIGN KEY(target_id) REFERENCES object_registry(object_id)
);

CREATE TABLE IF NOT EXISTS terminal_24d_forms (
  terminal_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  root_system TEXT NOT NULL,
  coxeter_number INTEGER,
  glue_code_json TEXT NOT NULL DEFAULT '{}',
  gram_hash TEXT,
  known_construction_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS glue_requirements (
  glue_id TEXT PRIMARY KEY,
  path_hash TEXT NOT NULL,
  target_id TEXT NOT NULL,
  source_id TEXT,
  required_cosets_json TEXT NOT NULL DEFAULT '[]',
  required_codewords_json TEXT NOT NULL DEFAULT '[]',
  validity_checks_json TEXT NOT NULL DEFAULT '{}',
  status TEXT NOT NULL DEFAULT 'template',
  FOREIGN KEY(target_id) REFERENCES terminal_24d_forms(terminal_id)
);

CREATE TABLE IF NOT EXISTS residue_registry (
  residue_id TEXT PRIMARY KEY,
  source_id TEXT,
  target_id TEXT,
  residue_type TEXT NOT NULL, -- prime, coprime, nsl, codeword, lattice, pariah
  payload_json TEXT NOT NULL DEFAULT '{}',
  status TEXT NOT NULL DEFAULT 'template'
);

CREATE TABLE IF NOT EXISTS rag_cards (
  card_id TEXT PRIMARY KEY,
  object_id TEXT NOT NULL,
  summary TEXT NOT NULL,
  known_facts TEXT NOT NULL DEFAULT '',
  admissible_futures TEXT NOT NULL DEFAULT '',
  obstructions TEXT NOT NULL DEFAULT '',
  references_json TEXT NOT NULL DEFAULT '[]',
  FOREIGN KEY(object_id) REFERENCES object_registry(object_id)
);



CREATE TABLE IF NOT EXISTS object_invariants (
  invariant_id TEXT PRIMARY KEY,
  object_id TEXT NOT NULL,
  invariant_type TEXT NOT NULL,
  payload_json TEXT NOT NULL DEFAULT '{}',
  status TEXT NOT NULL DEFAULT 'computed',
  hash TEXT NOT NULL,
  FOREIGN KEY(object_id) REFERENCES object_registry(object_id)
);

CREATE TABLE IF NOT EXISTS component_decompositions (
  component_id TEXT PRIMARY KEY,
  object_id TEXT NOT NULL,
  component_family TEXT NOT NULL,
  component_rank INTEGER NOT NULL,
  multiplicity INTEGER NOT NULL,
  component_root_count INTEGER NOT NULL,
  coxeter_number INTEGER,
  payload_json TEXT NOT NULL DEFAULT '{}',
  FOREIGN KEY(object_id) REFERENCES object_registry(object_id)
);

CREATE TABLE IF NOT EXISTS external_resource_registry (
  resource_id TEXT PRIMARY KEY,
  source TEXT NOT NULL,
  resource_type TEXT NOT NULL,
  query TEXT,
  title TEXT NOT NULL,
  url TEXT,
  status TEXT NOT NULL DEFAULT 'candidate',
  payload_json TEXT NOT NULL DEFAULT '{}'
);


CREATE TABLE IF NOT EXISTS discriminant_registry (
  discriminant_id TEXT PRIMARY KEY,
  object_id TEXT NOT NULL,
  root_lattice_determinant TEXT NOT NULL,
  discriminant_group_order TEXT NOT NULL,
  required_overlattice_index TEXT,
  glue_status TEXT NOT NULL DEFAULT 'template',
  payload_json TEXT NOT NULL DEFAULT '{}',
  hash TEXT NOT NULL,
  FOREIGN KEY(object_id) REFERENCES object_registry(object_id)
);

CREATE TABLE IF NOT EXISTS reflection_action_registry (
  action_id TEXT PRIMARY KEY,
  object_id TEXT NOT NULL,
  generator_index INTEGER NOT NULL,
  source_vector_id TEXT NOT NULL,
  target_vector_id TEXT NOT NULL,
  action_json TEXT NOT NULL DEFAULT '{}',
  hash TEXT NOT NULL,
  FOREIGN KEY(object_id) REFERENCES object_registry(object_id)
);

CREATE TABLE IF NOT EXISTS terminal_admissibility_profiles (
  profile_id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL,
  terminal_id TEXT NOT NULL,
  best_path_hash TEXT,
  min_depth INTEGER,
  status TEXT NOT NULL,
  payload_json TEXT NOT NULL DEFAULT '{}',
  hash TEXT NOT NULL,
  FOREIGN KEY(source_id) REFERENCES object_registry(object_id),
  FOREIGN KEY(terminal_id) REFERENCES terminal_24d_forms(terminal_id)
);

CREATE TABLE IF NOT EXISTS verification_runs (
  run_id TEXT PRIMARY KEY,
  created_utc TEXT NOT NULL,
  status TEXT NOT NULL,
  payload_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS path_registry (
  path_hash TEXT PRIMARY KEY,
  path_json TEXT NOT NULL,
  source_id TEXT NOT NULL,
  terminal_id TEXT,
  status TEXT NOT NULL,
  explanation TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_vectors_object ON exact_vectors(object_id);
CREATE INDEX IF NOT EXISTS idx_morphisms_source ON morphism_registry(source_id);
CREATE INDEX IF NOT EXISTS idx_morphisms_target ON morphism_registry(target_id);
CREATE INDEX IF NOT EXISTS idx_edges_source ON admissibility_edges(source_id);
CREATE INDEX IF NOT EXISTS idx_edges_target ON admissibility_edges(target_id);
CREATE INDEX IF NOT EXISTS idx_rag_object ON rag_cards(object_id);

CREATE INDEX IF NOT EXISTS idx_invariants_object ON object_invariants(object_id);
CREATE INDEX IF NOT EXISTS idx_components_object ON component_decompositions(object_id);
CREATE INDEX IF NOT EXISTS idx_external_source ON external_resource_registry(source, resource_type);
CREATE INDEX IF NOT EXISTS idx_discriminant_object ON discriminant_registry(object_id);
CREATE INDEX IF NOT EXISTS idx_reflection_actions_object ON reflection_action_registry(object_id, generator_index);


CREATE TABLE IF NOT EXISTS construction_status_registry (
  status_id TEXT PRIMARY KEY,
  object_id TEXT NOT NULL,
  surface_type TEXT NOT NULL,       -- exact_vectors, glue, morphism, group, boundary, nsl
  exactness TEXT NOT NULL,          -- exact, computed_profile, template, conceptual, pending_import
  payload_json TEXT NOT NULL DEFAULT '{}',
  hash TEXT NOT NULL,
  FOREIGN KEY(object_id) REFERENCES object_registry(object_id)
);

CREATE TABLE IF NOT EXISTS prime_factor_registry (
  factor_id TEXT PRIMARY KEY,
  object_id TEXT NOT NULL,
  integer_name TEXT NOT NULL,
  integer_value TEXT,
  factorization_json TEXT NOT NULL DEFAULT '{}',
  prime_set_json TEXT NOT NULL DEFAULT '[]',
  monster_compatible INTEGER,
  missing_monster_primes_json TEXT NOT NULL DEFAULT '[]',
  payload_json TEXT NOT NULL DEFAULT '{}',
  hash TEXT NOT NULL,
  FOREIGN KEY(object_id) REFERENCES object_registry(object_id)
);

CREATE TABLE IF NOT EXISTS path_metrics (
  metric_id TEXT PRIMARY KEY,
  path_hash TEXT NOT NULL,
  source_id TEXT NOT NULL,
  target_id TEXT,
  path_json TEXT NOT NULL,
  edge_count INTEGER NOT NULL,
  exact_edge_count INTEGER NOT NULL,
  template_edge_count INTEGER NOT NULL,
  conceptual_edge_count INTEGER NOT NULL,
  forbidden_edge_count INTEGER NOT NULL,
  evidence_level TEXT NOT NULL,
  status TEXT NOT NULL,
  payload_json TEXT NOT NULL DEFAULT '{}',
  hash TEXT NOT NULL,
  FOREIGN KEY(source_id) REFERENCES object_registry(object_id)
);

CREATE INDEX IF NOT EXISTS idx_terminal_profiles_source ON terminal_admissibility_profiles(source_id);


CREATE INDEX IF NOT EXISTS idx_construction_status_object ON construction_status_registry(object_id, surface_type);
CREATE INDEX IF NOT EXISTS idx_prime_factor_object ON prime_factor_registry(object_id);
CREATE INDEX IF NOT EXISTS idx_path_metrics_source ON path_metrics(source_id, target_id);

CREATE TABLE IF NOT EXISTS root_neighborhood_profiles (
  profile_id TEXT PRIMARY KEY,
  object_id TEXT NOT NULL,
  root_count INTEGER NOT NULL,
  unordered_pair_count INTEGER NOT NULL,
  inner_product_distribution_json TEXT NOT NULL DEFAULT '{}',
  norm_distribution_json TEXT NOT NULL DEFAULT '{}',
  status TEXT NOT NULL DEFAULT 'computed_exact',
  payload_json TEXT NOT NULL DEFAULT '{}',
  hash TEXT NOT NULL,
  FOREIGN KEY(object_id) REFERENCES object_registry(object_id)
);

CREATE TABLE IF NOT EXISTS root_adjacency_registry (
  adjacency_id TEXT PRIMARY KEY,
  object_id TEXT NOT NULL,
  source_vector_id TEXT NOT NULL,
  target_vector_id TEXT NOT NULL,
  inner_product_json TEXT NOT NULL,
  adjacency_kind TEXT NOT NULL,
  payload_json TEXT NOT NULL DEFAULT '{}',
  hash TEXT NOT NULL,
  FOREIGN KEY(object_id) REFERENCES object_registry(object_id)
);

CREATE TABLE IF NOT EXISTS morphism_witness_registry (
  witness_id TEXT PRIMARY KEY,
  morphism_id TEXT NOT NULL,
  source_id TEXT NOT NULL,
  target_id TEXT NOT NULL,
  witness_type TEXT NOT NULL,
  witness_vectors_json TEXT NOT NULL DEFAULT '[]',
  target_signature_json TEXT NOT NULL DEFAULT '{}',
  verification_status TEXT NOT NULL DEFAULT 'template',
  payload_json TEXT NOT NULL DEFAULT '{}',
  hash TEXT NOT NULL,
  FOREIGN KEY(source_id) REFERENCES object_registry(object_id),
  FOREIGN KEY(target_id) REFERENCES object_registry(object_id)
);

CREATE TABLE IF NOT EXISTS nsl_boundary_registry (
  nsl_id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL,
  target_id TEXT NOT NULL,
  noether_residue REAL NOT NULL,
  shannon_residue REAL NOT NULL,
  landauer_cost REAL NOT NULL,
  absorption_capacity REAL NOT NULL,
  theta REAL NOT NULL,
  closes_internally INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'dimensionless_proxy',
  payload_json TEXT NOT NULL DEFAULT '{}',
  hash TEXT NOT NULL,
  FOREIGN KEY(source_id) REFERENCES object_registry(object_id),
  FOREIGN KEY(target_id) REFERENCES object_registry(object_id)
);

CREATE TABLE IF NOT EXISTS build_manifest_registry (
  manifest_id TEXT PRIMARY KEY,
  package_version TEXT NOT NULL,
  created_utc TEXT NOT NULL,
  db_schema_label TEXT NOT NULL,
  payload_json TEXT NOT NULL DEFAULT '{}',
  hash TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_root_neighborhood_object ON root_neighborhood_profiles(object_id);
CREATE INDEX IF NOT EXISTS idx_root_adjacency_object ON root_adjacency_registry(object_id, adjacency_kind);
CREATE INDEX IF NOT EXISTS idx_morphism_witness_source ON morphism_witness_registry(source_id, target_id);
CREATE INDEX IF NOT EXISTS idx_nsl_boundary_source ON nsl_boundary_registry(source_id, target_id);


CREATE TABLE IF NOT EXISTS dynkin_registry (
  dynkin_id TEXT PRIMARY KEY,
  object_id TEXT NOT NULL,
  cartan_matrix_json TEXT NOT NULL,
  determinant_json TEXT NOT NULL,
  coxeter_number INTEGER,
  root_count INTEGER,
  simple_root_count INTEGER,
  status TEXT NOT NULL DEFAULT 'computed_exact',
  payload_json TEXT NOT NULL DEFAULT '{}',
  hash TEXT NOT NULL,
  FOREIGN KEY(object_id) REFERENCES object_registry(object_id)
);

CREATE TABLE IF NOT EXISTS terminal_component_embeddings (
  embedding_id TEXT PRIMARY KEY,
  terminal_id TEXT NOT NULL,
  component_label TEXT NOT NULL,
  component_instance_index INTEGER NOT NULL,
  source_id TEXT NOT NULL,
  rank_offset INTEGER NOT NULL,
  root_vector_count INTEGER NOT NULL,
  source_vector_ids_json TEXT NOT NULL DEFAULT '[]',
  terminal_vector_ids_json TEXT NOT NULL DEFAULT '[]',
  status TEXT NOT NULL DEFAULT 'computed_exact_root_shell_embedding',
  payload_json TEXT NOT NULL DEFAULT '{}',
  hash TEXT NOT NULL,
  FOREIGN KEY(terminal_id) REFERENCES object_registry(object_id),
  FOREIGN KEY(source_id) REFERENCES object_registry(object_id)
);

CREATE TABLE IF NOT EXISTS morphism_verification_registry (
  verification_id TEXT PRIMARY KEY,
  morphism_id TEXT NOT NULL,
  source_id TEXT NOT NULL,
  target_id TEXT NOT NULL,
  verification_type TEXT NOT NULL,
  source_signature_json TEXT NOT NULL DEFAULT '{}',
  target_signature_json TEXT NOT NULL DEFAULT '{}',
  result TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'computed',
  payload_json TEXT NOT NULL DEFAULT '{}',
  hash TEXT NOT NULL,
  FOREIGN KEY(source_id) REFERENCES object_registry(object_id),
  FOREIGN KEY(target_id) REFERENCES object_registry(object_id)
);

CREATE TABLE IF NOT EXISTS closure_obstruction_registry (
  obstruction_id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL,
  target_id TEXT NOT NULL,
  obstruction_type TEXT NOT NULL,
  condition_json TEXT NOT NULL DEFAULT '{}',
  result TEXT NOT NULL,
  severity TEXT NOT NULL DEFAULT 'info',
  payload_json TEXT NOT NULL DEFAULT '{}',
  hash TEXT NOT NULL,
  FOREIGN KEY(source_id) REFERENCES object_registry(object_id),
  FOREIGN KEY(target_id) REFERENCES object_registry(object_id)
);

CREATE INDEX IF NOT EXISTS idx_dynkin_object ON dynkin_registry(object_id);
CREATE INDEX IF NOT EXISTS idx_terminal_component_embeddings_terminal ON terminal_component_embeddings(terminal_id, source_id);
CREATE INDEX IF NOT EXISTS idx_morphism_verification_source ON morphism_verification_registry(source_id, target_id);
CREATE INDEX IF NOT EXISTS idx_closure_obstruction_source ON closure_obstruction_registry(source_id, target_id);

"""
