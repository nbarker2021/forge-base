/**
 * EntropyClient — TypeScript SDK for EntropyCore API
 */

import type {
  EntropyBlock,
  GenerationProof,
  FairnessCommitment,
  FairnessReveal,
  BatchResult,
  HealthResponse,
  StreamBlock,
} from './types';

const DEFAULT_TIMEOUT = 30000;

export class EntropyClient {
  private baseUrl: string;
  private timeout: number;

  constructor(baseUrl: string = 'http://localhost:8000', timeout: number = DEFAULT_TIMEOUT) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.timeout = timeout;
  }

  private async post(path: string, body: Record<string, unknown>): Promise<Record<string, unknown>> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeout);

    try {
      const resp = await fetch(`${this.baseUrl}${path}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'User-Agent': 'entropy-core-ts/1.0.0',
        },
        body: JSON.stringify(body),
        signal: controller.signal,
      });
      clearTimeout(timer);
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}: ${await resp.text()}`);
      }
      return await resp.json();
    } catch (e) {
      clearTimeout(timer);
      throw e;
    }
  }

  private async get(path: string): Promise<Record<string, unknown>> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeout);

    try {
      const resp = await fetch(`${this.baseUrl}${path}`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
          'User-Agent': 'entropy-core-ts/1.0.0',
        },
        signal: controller.signal,
      });
      clearTimeout(timer);
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}: ${await resp.text()}`);
      }
      return await resp.json();
    } catch (e) {
      clearTimeout(timer);
      throw e;
    }
  }

  /**
   * Check API health
   */
  async health(): Promise<HealthResponse> {
    const data = await this.get('/health');
    return data as HealthResponse;
  }

  /**
   * Generate secure random bytes with proof
   */
  async randomBytes(size: number = 32, includeProof: boolean = true): Promise<EntropyBlock> {
    const data = await this.post('/v1/secure-random', {
      size_bytes: size,
      include_proof: includeProof,
    });
    return this.parseBlock(data);
  }

  /**
   * High-throughput batch generation
   */
  async batch(
    blockSize: number = 4096,
    blockCount: number = 100,
    includeProofs: boolean = false,
  ): Promise<BatchResult> {
    const data = await this.post('/v1/batch-gen', {
      block_size: blockSize,
      block_count: blockCount,
      include_proofs: includeProofs,
    });

    const blocks = (data.blocks as Record<string, unknown>[] || [])
      .map(b => this.parseBlock(b));

    return {
      blocks,
      total_bytes: (data.total_bytes as number) || 0,
      total_blocks: (data.total_blocks as number) || 0,
      generation_time_ms: (data.generation_time_ms as number) || 0,
      throughput_mbps: (data.throughput_mbps as number) || 0,
    };
  }

  /**
   * Create a fairness commitment for provably fair randomness
   */
  async commit(description: string = ''): Promise<FairnessCommitment> {
    const data = await this.post('/v1/fairness-proof', {
      description,
    });
    const commitment = data.commitment as Record<string, string>;
    return {
      id: commitment.commitment_hash.substring(0, 16),
      hash: commitment.commitment_hash,
      salt: commitment.salt,
      public_info: commitment.public_info,
      created_at: commitment.created_at,
      reveal_at: commitment.reveal_at,
    };
  }

  /**
   * Reveal a fairness commitment
   */
  async reveal(commitmentId: string): Promise<FairnessReveal> {
    const data = await this.get(`/v1/fairness-proof/${commitmentId}/reveal`);
    const reveal = data.reveal as Record<string, unknown>;
    const b64 = reveal.random_bytes_b64 as string;
    const bytes = b64 ? Uint8Array.from(atob(b64), c => c.charCodeAt(0)) : new Uint8Array();

    return {
      random_bytes: bytes,
      salt: (reveal.salt as string) || '',
      nonce: (reveal.nonce as number) || 0,
      seed_hash: (reveal.seed_hash as string) || '',
      verified: (data.verification as Record<string, unknown>)?.commitment_verified === true,
    };
  }

  /**
   * Stream random bytes via WebSocket
   */
  async *stream(totalBytes: number = 65536, blockSize: number = 4096): AsyncGenerator<EntropyBlock> {
    const wsUrl = this.baseUrl
      .replace(/^http:\/\//, 'ws://')
      .replace(/^https:\/\//, 'wss://');

    const ws = new WebSocket(`${wsUrl}/v1/stream`);

    let resolveMessage: ((value: unknown) => void) | null = null;
    let rejectMessage: ((error: Error) => void) | null = null;
    const messageQueue: unknown[] = [];
    let closed = false;

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (resolveMessage) {
        resolveMessage(data);
        resolveMessage = null;
      } else {
        messageQueue.push(data);
      }
    };

    ws.onclose = () => { closed = true; };
    ws.onerror = (err) => {
      if (rejectMessage) rejectMessage(new Error('WebSocket error'));
    };

    await new Promise<void>((resolve, reject) => {
      ws.onopen = () => resolve();
      ws.onerror = () => reject(new Error('WebSocket connection failed'));
    });

    ws.send(JSON.stringify({ total_bytes: totalBytes, block_size: blockSize }));

    try {
      while (!closed) {
        const msg = messageQueue.length > 0
          ? messageQueue.shift()
          : await new Promise((res, rej) => { resolveMessage = res; rejectMessage = rej; });

        const data = msg as Record<string, unknown>;
        if (data.type === 'complete') break;
        if (data.type === 'error') throw new Error(data.message as string);
        if (data.bytes_b64) {
          yield this.parseBlock(data);
        }
      }
    } finally {
      ws.close();
    }
  }

  private parseBlock(data: Record<string, unknown>): EntropyBlock {
    const b64 = (data.bytes_b64 as string) || '';
    const bytes = b64 ? Uint8Array.from(atob(b64), c => c.charCodeAt(0)) : new Uint8Array();
    const hex = Array.from(bytes)
      .map(b => b.toString(16).padStart(2, '0'))
      .join('');

    const proofData = data.proof as Record<string, unknown> | undefined;
    let proof: GenerationProof | undefined;

    if (proofData) {
      const voaPart = proofData.voa_partition as Record<string, unknown> | undefined;
      proof = {
        block_index: (proofData.block_index as number) || 0,
        chart_sequence: (proofData.chart_sequence as number[][]) || [],
        syndrome_id: (proofData.syndrome_id as string) || '',
        seed_hash: (proofData.seed_hash as string) || '',
        timestamp: (proofData.timestamp as string) || '',
        voa_partition: {
          weight_distribution: (voaPart?.weight_distribution as Record<string, number>) || {},
          vacuum_fraction: (voaPart?.vacuum_fraction as number) || 0,
          excited_fraction: (voaPart?.excited_fraction as number) || 0,
          seed_partition_function: 'Z(q) = 2q^0 + 6q^5',
          monster_scalar: (voaPart?.monster_scalar as number) || 196883,
        },
        monster_scalar: (proofData.monster_scalar as number) || 196883,
      };
    }

    return {
      bytes_b64: b64,
      bytes_data: bytes,
      bytesHex: hex,
      size_bytes: (data.size_bytes as number) || 0,
      proof,
      chart_density: (data.chart_density as number) || 0,
      correction_rate: (data.correction_rate as number) || 0,
      generation_time_ms: (data.generation_time_ms as number) || 0,
      toDict: () => ({
        bytes_b64: b64,
        size_bytes: data.size_bytes || 0,
        proof: proofData || null,
        chart_density: data.chart_density || 0,
        correction_rate: data.correction_rate || 0,
      }),
    };
  }
}
