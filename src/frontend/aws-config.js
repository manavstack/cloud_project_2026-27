/**
 * aws-config.js — Federated Campus Energy Cloud
 *
 * Fill in the values below after running:  sam deploy --guided
 * The outputs are printed at the end of the SAM deploy command.
 *
 * IMPORTANT: This file contains ONLY public identifiers (no secrets).
 * It is safe to commit. Secrets live in Lambda environment variables only.
 *
 * ─────────────────────────────────────────────────────────────────────────
 * Until you fill in real values the dashboard runs in Demo Mode automatically
 * — all data is simulated and no AWS account is needed.
 * ─────────────────────────────────────────────────────────────────────────
 */

window.AWS_CONFIG = {
  // AWS region where the SAM stack was deployed
  region: 'ap-south-1',

  // ── Amazon Cognito ──────────────────────────────────────────────────────
  // SAM output: UserPoolId, UserPoolClientId
  cognito: {
    userPoolId:          'ap-south-1_2bm4YeRJ5',
    userPoolWebClientId: '5sitauocubcvtqbhh0birfiafv',
  },

  // ── API Gateway (REST) ──────────────────────────────────────────────────
  // SAM output: RestApiUrl
  apiGateway: {
    restUrl: 'https://nzkopoif4a.execute-api.ap-south-1.amazonaws.com/prod',
  },

  // ── API Gateway (WebSocket) ─────────────────────────────────────────────
  // SAM output: WebSocketApiUrl
  // Used for real-time IoT Core → dashboard push
  websocket: {
    url: 'wss://8gdus6lq60.execute-api.ap-south-1.amazonaws.com/prod',
  },

  // ── Amazon S3 ───────────────────────────────────────────────────────────
  // SAM output: ExportBucketName
  s3: {
    exportBucket: 'campus-energy-exports-585384908183-ap-south-1',
  },
};

// ── Internal: detect Demo vs Live mode ─────────────────────────────────────
// Do not edit below this line.
(function detectMode() {
  const cfg = window.AWS_CONFIG;
  const isPlaceholder = (v) => !v || v === 'REPLACE_ME';
  window.AWS_DEMO_MODE = (
    isPlaceholder(cfg.cognito.userPoolId) ||
    isPlaceholder(cfg.apiGateway.restUrl)
  );
  if (window.AWS_DEMO_MODE) {
    console.info(
      '%c[Campus Energy] Demo Mode — simulated data active. ' +
      'Fill in aws-config.js with SAM deploy outputs to switch to Live Mode.',
      'color:#0a7860;font-weight:bold'
    );
  } else {
    console.info(
      '%c[Campus Energy] Live Mode — AWS services connected.',
      'color:#16a34a;font-weight:bold'
    );
  }
})();
