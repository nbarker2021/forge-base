/**
 * EntropyCore TypeScript SDK
 * ==========================
 *
 * npm install entropy-core
 *
 * Usage:
 *   import { EntropyClient } from 'entropy-core';
 *
 *   const client = new EntropyClient('http://localhost:8000');
 *
 *   // Generate secure random bytes
 *   const block = await client.randomBytes(32);
 *   console.log(block.bytesHex);
 *   console.log(block.proof.syndromeId);  // non-periodicity proof
 *
 *   // Verify
 *   const result = verifyBlock(block);
 *   console.log(result.status);  // "valid"
 *
 *   // Fairness commitment
 *   const commitment = await client.commit('Lottery #42');
 *   const reveal = await client.reveal(commitment.id);
 */

export { EntropyClient } from './client';
export {
  verifyBlock,
  verifyStream,
  verifySyndrome,
  VOA_PARTITION,
  MONSTER_SCALAR,
} from './verify';
export type {
  EntropyBlock,
  GenerationProof,
  FairnessCommitment,
  FairnessReveal,
  BatchResult,
  VerificationResult,
  StreamBlock,
} from './types';

export const VERSION = '1.0.0';
