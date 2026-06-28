/**
 * Type definitions for EntropyCore TypeScript SDK
 */

export interface VOAPartitionProof {
  weight_distribution: Record<string, number>;
  vacuum_fraction: number;
  excited_fraction: number;
  seed_partition_function: string;
  monster_scalar: number;
}

export interface GenerationProof {
  block_index: number;
  chart_sequence: number[][];
  syndrome_id: string;
  seed_hash: string;
  timestamp: string;
  voa_partition: VOAPartitionProof;
  monster_scalar: number;
}

export interface EntropyBlock {
  bytes_b64: string;
  bytes_data: Uint8Array;
  bytesHex: string;
  size_bytes: number;
  proof?: GenerationProof;
  chart_density: number;
  correction_rate: number;
  generation_time_ms: number;
  toDict(): Record<string, unknown>;
}

export interface FairnessCommitment {
  id: string;
  hash: string;
  salt: string;
  public_info: string;
  created_at: string;
  reveal_at?: string;
}

export interface FairnessReveal {
  random_bytes: Uint8Array;
  salt: string;
  nonce: number;
  seed_hash: string;
  verified: boolean;
}

export interface BatchResult {
  blocks: EntropyBlock[];
  total_bytes: number;
  total_blocks: number;
  generation_time_ms: number;
  throughput_mbps: number;
}

export interface VerificationResult {
  status: 'valid' | 'invalid';
  errors: string[];
  voa_weight_distribution?: Record<string, number>;
  vacuum_fraction?: number;
  monster_scalar_match?: boolean;
  syndrome_format_valid?: boolean;
}

export interface StreamBlock {
  block_index: number;
  bytes_b64: string;
  syndrome_id: string;
  previous_syndrome_hash: string;
  timestamp: string;
  checksum_valid: boolean;
}

export interface HealthResponse {
  status: string;
  version: string;
  engine: string;
  timestamp: string;
  uptime_seconds: number;
  blocks_generated: number;
  total_bytes_generated: number;
}
