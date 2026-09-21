// Initial clean state for CrossContext (zero demo data)
export const DEFAULT_NODES: any[] = []
export const DEFAULT_EDGES: any[] = []

export const DEFAULT_STATS = {
  repositories: [] as string[],
  total_symbols: 0,
  total_edges: 0,
  cross_repo_edges: 0,
  db_engine: 'AWS OpenSearch Serverless',
  runtime_env: 'aws',
  aws: {
    connected: true,
    mode: 'aws_bedrock_live',
    region: 'us-west-2',
    active_model: 'us.anthropic.claude-sonnet-4-5-20250929-v1:0',
    embedding_model: 'amazon.titan-embed-text-v2:0',
  },
}
