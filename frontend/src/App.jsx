import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import SidebarDocuments from './SidebarDocuments.jsx';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

function useAsyncState(initial) {
  const [state, setState] = useState(initial);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const wrap = async (fn) => {
    setLoading(true);
    setError(null);
    try {
      const result = await fn();
      setState(result);
      return result;
    } catch (e) {
      console.error(e);
      setError(e instanceof Error ? e.message : String(e));
      throw e;
    } finally {
      setLoading(false);
    }
  };

  return { state, setState, loading, error, wrap };
}

function App() {
  // Upload form state
  const [docId, setDocId] = useState('');
  const [docText, setDocText] = useState('');
  const [uploadMessage, setUploadMessage] = useState(null);

  // Shared query for semantic + hybrid
  const [query, setQuery] = useState('');

  // Semantic search state
  const semantic = useAsyncState({ results: [], results_count: 0, query: '' });

  // Hybrid search state
  const hybrid = useAsyncState({
    vector_hits: [],
    vector_hits_count: 0,
    graph_expansion: [],
    graph_expansion_count: 0,
    entities: [],
    entities_count: 0,
    hybrid_results: [],
    hybrid_results_count: 0,
    query: '',
  });

  // Stats state
  const stats = useAsyncState(null);

  const fetchStats = useCallback(() => {
    return stats
      .wrap(async () => {
        const res = await fetch(`${API_BASE_URL}/stats`);
        if (!res.ok) {
          throw new Error(`Stats request failed: ${res.status}`);
        }
        return res.json();
      })
      .catch(() => undefined);
  }, [stats]);

  // Relationships state
  const [relDocId, setRelDocId] = useState('');
  const [relDepth, setRelDepth] = useState('2');
  const relationships = useAsyncState(null);
  const neighbors = useAsyncState(null);

  const topSemanticResults = useMemo(() => {
    if (!semantic.state || !semantic.state.results) return [];
    return semantic.state.results.slice(0, 10);
  }, [semantic.state]);

  // Auto-refresh stats every 5 seconds
  useEffect(() => {
    fetchStats();
    const id = setInterval(fetchStats, 5000);
    return () => clearInterval(id);
  }, [fetchStats]);

  const handleAddDocument = async (e) => {
    e.preventDefault();
    setUploadMessage(null);
    if (!docId.trim() || !docText.trim()) {
      setUploadMessage({ type: 'error', text: 'Please provide both doc_id and text.' });
      return;
    }

    try {
      const res = await fetch(`${API_BASE_URL}/add_document`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ doc_id: docId.trim(), text: docText, metadata: {} }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Upload failed with status ${res.status}`);
      }

      const data = await res.json();
      setUploadMessage({
        type: 'success',
        text: `Document added. Entities extracted: ${data.entities_extracted ?? 0}.`,
      });
      setDocId('');
      setDocText('');
    } catch (err) {
      setUploadMessage({ type: 'error', text: err.message || 'Failed to add document.' });
    }
  };

  const handleSemanticSearch = async () => {
    if (!query.trim()) return;
    await semantic.wrap(async () => {
      const url = new URL(`${API_BASE_URL}/search`);
      url.searchParams.set('q', query.trim());
      url.searchParams.set('top_k', '10');
      const res = await fetch(url);
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Search failed with status ${res.status}`);
      }
      return res.json();
    });
  };

  const handleHybridSearch = async () => {
    if (!query.trim()) return;
    await hybrid.wrap(async () => {
      const url = new URL(`${API_BASE_URL}/hybrid`);
      url.searchParams.set('q', query.trim());
      url.searchParams.set('top_k', '5');
      url.searchParams.set('depth', '2');
      const res = await fetch(url);
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Hybrid search failed with status ${res.status}`);
      }
      return res.json();
    });
  };

  const handleGetRelationships = async () => {
    const id = relDocId.trim();
    if (!id) return;

    // Relationships by entities
    relationships.wrap(async () => {
      const res = await fetch(`${API_BASE_URL}/relationships/${encodeURIComponent(id)}`);
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Relationships failed with status ${res.status}`);
      }
      return res.json();
    }).catch(() => undefined);

    // Graph neighbors for optional extra info
    neighbors.wrap(async () => {
      const url = new URL(`${API_BASE_URL}/graph_neighbors`);
      url.searchParams.set('doc_id', id);
      url.searchParams.set('depth', relDepth || '2');
      const res = await fetch(url);
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Graph neighbors failed with status ${res.status}`);
      }
      return res.json();
    }).catch(() => undefined);
  };

  const renderSnippet = (text) => {
    if (!text) return '';
    if (text.length <= 220) return text;
    return text.slice(0, 220) + '…';
  };

  return (
    <div className="app-container">
      <aside className="sidebar-column">
        <SidebarDocuments onStatsChange={fetchStats} />
      </aside>

      <div className="left-column">
        <header className="app-header">
          <h1>Hybrid Vector + Graph Search</h1>
          <p className="subtitle">Add documents, run semantic & hybrid search</p>
        </header>

        {/* SECTION 1 — DOCUMENT UPLOAD PANEL */}
        <section className="card" id="upload-panel">
          <h2>Add Document</h2>
          <form onSubmit={handleAddDocument}>
            <div className="field-group">
              <label htmlFor="doc-id">Document ID</label>
              <input
                id="doc-id"
                type="text"
                placeholder="e.g. doc1"
                value={docId}
                onChange={(e) => setDocId(e.target.value)}
              />
            </div>
            <div className="field-group">
              <label htmlFor="doc-text">Document Text</label>
              <textarea
                id="doc-text"
                rows={6}
                placeholder="Paste or type your document text here..."
                value={docText}
                onChange={(e) => setDocText(e.target.value)}
              />
            </div>
            <div className="button-row">
              <button type="submit" disabled={semantic.loading || hybrid.loading}>
                {semantic.loading || hybrid.loading ? 'Working...' : 'Add Document'}
              </button>
            </div>
            <p className="helper-text">
              Sends <code>POST /add_document</code> with <code>doc_id</code>, <code>text</code>, and empty
              <code> metadata</code>.
            </p>
            {uploadMessage && (
              <p className={uploadMessage.type === 'error' ? 'error-text' : 'success-text'}>
                {uploadMessage.text}
              </p>
            )}
          </form>
        </section>

        {/* SECTION 2 & 3 — SEARCH INPUT */}
        <section className="card" id="search-panel">
          <h2>Search</h2>
          <div className="field-group">
            <label htmlFor="search-query">Search Query</label>
            <input
              id="search-query"
              type="text"
              placeholder="e.g. deep learning and neural networks"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
          <div className="button-row">
            <button type="button" onClick={handleSemanticSearch} disabled={semantic.loading}>
              {semantic.loading ? 'Searching…' : 'Semantic Search'}
            </button>
            <button type="button" onClick={handleHybridSearch} disabled={hybrid.loading}>
              {hybrid.loading ? 'Searching…' : 'Hybrid Search'}
            </button>
          </div>
          <p className="helper-text">
            Semantic: <code>GET /search?q=&lt;query&gt;&amp;top_k=10</code> &nbsp; | &nbsp; Hybrid:{' '}
            <code>GET /hybrid?q=&lt;query&gt;&amp;top_k=5&amp;depth=2</code>
          </p>
          {semantic.error && <p className="error-text">Semantic search error: {semantic.error}</p>}
          {hybrid.error && <p className="error-text">Hybrid search error: {hybrid.error}</p>}
        </section>

        {/* SECTION 2 — SEMANTIC SEARCH RESULTS */}
        <section className="card" id="semantic-results-card">
          <h2>Semantic Search Results</h2>
          <div className={
            'results-section ' + (topSemanticResults.length === 0 ? 'empty-state' : '')
          }>
            {topSemanticResults.length === 0 ? (
              <p>No results yet. Run a semantic search.</p>
            ) : (
              topSemanticResults.map((res) => (
                <div key={res.doc_id + String(res.distance)} className="result-item">
                  <div className="result-header">
                    <div className="doc-id">Doc: {res.doc_id}</div>
                    <div>
                      <span className="score-pill">
                        Score: {typeof res.relevance_score === 'number'
                          ? res.relevance_score.toFixed(4)
                          : 'N/A'}
                      </span>
                    </div>
                  </div>
                  <div className="snippet">{renderSnippet(res.document)}</div>
                  {res.metadata && Object.keys(res.metadata).length > 0 && (
                    <div className="meta-line">Metadata: {JSON.stringify(res.metadata)}</div>
                  )}
                </div>
              ))
            )}
          </div>
        </section>

        {/* SECTION 3 — HYBRID SEARCH RESULTS */}
        <section className="card" id="hybrid-results-card">
          <h2>Hybrid Search Results</h2>
          <div className="results-section">
            {(!hybrid.state || hybrid.state.hybrid_results_count === 0) && (
              <p className="helper-text">No hybrid results yet. Run a hybrid search.</p>
            )}

            {hybrid.state && hybrid.state.vector_hits_count > 0 && (
              <div>
                <div className="section-title-sm">1. Vector Hits</div>
                {hybrid.state.vector_hits.map((res) => (
                  <div key={'vec-' + res.doc_id + String(res.distance)} className="result-item">
                    <div className="result-header">
                      <div className="doc-id">Doc: {res.doc_id}</div>
                      <div>
                        <span className="score-pill">
                          Score: {typeof res.relevance_score === 'number'
                            ? res.relevance_score.toFixed(4)
                            : 'N/A'}
                        </span>
                        <span className="source-pill">vector</span>
                      </div>
                    </div>
                    <div className="snippet">{renderSnippet(res.document)}</div>
                    <div className="meta-line">
                      Graph neighbors: {res.graph_neighbors_count ?? 0}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {hybrid.state && hybrid.state.graph_expansion_count > 0 && (
              <div>
                <div className="section-title-sm">2. Graph Expansion Results</div>
                {hybrid.state.graph_expansion.map((res) => (
                  <div key={'graph-' + res.doc_id} className="result-item">
                    <div className="result-header">
                      <div className="doc-id">Doc: {res.doc_id}</div>
                      <div>
                        <span className="source-pill">graph_expansion</span>
                      </div>
                    </div>
                    <div className="snippet">{renderSnippet(res.document)}</div>
                  </div>
                ))}

                {hybrid.state.entities_count > 0 && (
                  <div className="meta-line">
                    <span className="section-title-sm">Top Entities</span>
                    <ul className="entity-list">
                      {hybrid.state.entities.slice(0, 10).map((e) => (
                        <li key={e.entity}>
                          <span className="badge">{e.entity}</span>
                          <span>
                            related docs: {e.related_document_count}{' '}
                            {e.related_documents && e.related_documents.length > 0 &&
                              `(${e.related_documents.join(', ')})`}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {hybrid.state && hybrid.state.hybrid_results_count > 0 && (
              <div>
                <div className="section-title-sm">3. Combined Hybrid Ranking</div>
                {hybrid.state.hybrid_results.map((res, idx) => (
                  <div key={'hyb-' + res.doc_id + '-' + idx} className="result-item">
                    <div className="result-header">
                      <div className="doc-id">Doc: {res.doc_id}</div>
                      <div>
                        {typeof res.relevance_score === 'number' && (
                          <span className="score-pill">
                            Score: {res.relevance_score.toFixed(4)}
                          </span>
                        )}
                        <span className="source-pill">{res.source}</span>
                      </div>
                    </div>
                    <div className="snippet">{renderSnippet(res.document)}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>
      </div>

      {/* RIGHT COLUMN: stats + relationships */}
      <aside className="right-column">
        {/* SECTION 4 — SYSTEM STATISTICS */}
        <section className="card" id="stats-panel">
          <h2>System Statistics</h2>
          <p className="helper-text">
            Auto-refreshes every 5 seconds from <code>GET /stats</code>.
          </p>
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-label">Documents (Chroma)</div>
              <div className="stat-value">
                {stats.state?.chromadb?.total_documents ?? '–'}
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Total Nodes</div>
              <div className="stat-value">
                {stats.state?.graph?.total_nodes ?? '–'}
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Total Edges</div>
              <div className="stat-value">
                {stats.state?.graph?.total_edges ?? '–'}
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Document Nodes</div>
              <div className="stat-value">
                {stats.state?.graph?.document_nodes ?? '–'}
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Entity Nodes</div>
              <div className="stat-value">
                {stats.state?.graph?.entity_nodes ?? '–'}
              </div>
            </div>
            <div className="stat-card small">
              <div className="stat-label">Status</div>
              <div className="stat-value small">
                {stats.state?.system?.status ?? '–'}
              </div>
            </div>
          </div>
          {stats.error && <p className="error-text">Stats error: {stats.error}</p>}
        </section>

        {/* SECTION 5 — GRAPH RELATIONSHIP VIEWER */}
        <section className="card" id="graph-viewer-panel">
          <h2>Graph Relationships</h2>
          <div className="field-group">
            <label htmlFor="relationship-doc-id">Document ID</label>
            <input
              id="relationship-doc-id"
              type="text"
              placeholder="e.g. doc1"
              value={relDocId}
              onChange={(e) => setRelDocId(e.target.value)}
            />
          </div>
          <div className="field-group">
            <label htmlFor="relationship-depth">Depth</label>
            <select
              id="relationship-depth"
              value={relDepth}
              onChange={(e) => setRelDepth(e.target.value)}
            >
              <option value="1">1</option>
              <option value="2">2</option>
            </select>
          </div>
          <div className="button-row">
            <button
              type="button"
              onClick={handleGetRelationships}
              disabled={relationships.loading || neighbors.loading}
            >
              {relationships.loading || neighbors.loading
                ? 'Loading…'
                : 'Get Relationships'}
            </button>
          </div>
          <p className="helper-text">
            Uses <code>GET /relationships/&lt;doc_id&gt;</code> and{' '}
            <code>GET /graph_neighbors?doc_id=&lt;doc_id&gt;&amp;depth=&lt;depth&gt;</code>.
          </p>

          <div className="results-section">
            {!relationships.state && !neighbors.state && (
              <p className="helper-text">
                Enter a document ID to see its entities, related documents, and neighbors.
              </p>
            )}

            {relationships.error && (
              <p className="error-text">Relationships error: {relationships.error}</p>
            )}
            {neighbors.error && <p className="error-text">Neighbors error: {neighbors.error}</p>}

            {relationships.state && (
              <div>
                <div className="section-title-sm">Entities connected to document</div>
                {relationships.state.entities_count === 0 ? (
                  <p className="helper-text">No entities found in graph for this document.</p>
                ) : (
                  <ul className="entity-list">
                    {relationships.state.entities.map((e) => (
                      <li key={e}>
                        <span className="badge">{e}</span>
                        <span>
                          related docs:{' '}
                          {relationships.state.related_via_entities?.[e]?.join(', ') || 'none'}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}

                <div className="section-title-sm">Related documents (via entities)</div>
                {relationships.state.related_documents_count === 0 ? (
                  <p className="helper-text">No related documents found via entities.</p>
                ) : (
                  <ul className="doc-list">
                    {relationships.state.related_documents.map((d) => (
                      <li key={d}>{d}</li>
                    ))}
                  </ul>
                )}
              </div>
            )}

            {neighbors.state && (
              <div>
                <div className="section-title-sm">Graph neighbors (depth {neighbors.state.depth})</div>
                <p className="meta-line">
                  Total neighbors: {neighbors.state.total_neighbors} · Documents:{' '}
                  {neighbors.state.document_neighbors_count} · Entities:{' '}
                  {neighbors.state.entity_neighbors_count}
                </p>
                <ul className="neighbor-list">
                  {neighbors.state.all_neighbors?.map((n) => (
                    <li key={n}>{n}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </section>

        {/* SECTION 6 — GRAPH VISUALIZATION */}
        <section className="card" id="graph-visualization-panel">
          <h2>Graph Visualization</h2>
          <p className="helper-text">
            Visual representation of nodes and edges from the relationship query above.
          </p>
          <GraphVisualization
            relationshipsData={relationships.state}
            neighborsData={neighbors.state}
            docId={relDocId}
          />
        </section>
      </aside>
    </div>
  );
}

// Graph Visualization Component
function GraphVisualization({ relationshipsData, neighborsData, docId }) {
  const canvasRef = useRef(null);
  const [hoveredNode, setHoveredNode] = useState(null);
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [draggedNode, setDraggedNode] = useState(null);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });

  // Build nodes and edges when data changes
  useEffect(() => {
    if (!relationshipsData) {
      setNodes([]);
      setEdges([]);
      return;
    }
    if (!canvasRef.current) return;

    const canvas = canvasRef.current;
    const width = canvas.width;
    const height = canvas.height;

    // Build nodes and edges from data
    const newNodes = [];
    const newEdges = [];

    if (relationshipsData && docId) {
      // Central document node (blue)
      newNodes.push({
        id: docId,
        label: docId,
        type: 'document',
        x: width / 2,
        y: height / 2,
      });

      // Entity nodes (green) connected to the document
      const entities = relationshipsData.entities || [];
      const angleStep = (2 * Math.PI) / Math.max(entities.length, 1);
      const radius = 120;

      entities.forEach((entity, idx) => {
        const angle = idx * angleStep;
        const x = width / 2 + radius * Math.cos(angle);
        const y = height / 2 + radius * Math.sin(angle);

        newNodes.push({
          id: entity,
          label: entity,
          type: 'entity',
          x,
          y,
        });

        // Edge from document to entity
        newEdges.push({
          from: docId,
          to: entity,
        });
      });

      // Related documents (blue) - outer ring
      const relatedDocs = relationshipsData.related_documents || [];
      const outerRadius = 200;
      const outerAngleStep = (2 * Math.PI) / Math.max(relatedDocs.length, 1);

      relatedDocs.forEach((doc, idx) => {
        const angle = idx * outerAngleStep;
        const x = width / 2 + outerRadius * Math.cos(angle);
        const y = height / 2 + outerRadius * Math.sin(angle);

        // Check if node already exists
        if (!newNodes.find(n => n.id === doc)) {
          newNodes.push({
            id: doc,
            label: doc,
            type: 'document',
            x,
            y,
          });
        }

        // Find common entities to connect through
        entities.forEach((entity) => {
          const relatedViaEntity = relationshipsData.related_via_entities?.[entity] || [];
          if (relatedViaEntity.includes(doc)) {
            newEdges.push({
              from: entity,
              to: doc,
            });
          }
        });
      });
    }

    setNodes(newNodes);
    setEdges(newEdges);
  }, [relationshipsData, docId]);

  // Draw the graph
  useEffect(() => {
    if (!canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

    // Clear canvas
    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = '#020617';
    ctx.fillRect(0, 0, width, height);

    if (nodes.length === 0) return;

    // Save context and apply transformations
    ctx.save();
    ctx.translate(pan.x, pan.y);
    ctx.scale(zoom, zoom);

    // Draw edges
    ctx.strokeStyle = '#1f2937';
    ctx.lineWidth = 2 / zoom;
    edges.forEach(edge => {
      const fromNode = nodes.find(n => n.id === edge.from);
      const toNode = nodes.find(n => n.id === edge.to);
      if (fromNode && toNode) {
        ctx.beginPath();
        ctx.moveTo(fromNode.x, fromNode.y);
        ctx.lineTo(toNode.x, toNode.y);
        ctx.stroke();
      }
    });

    // Draw nodes
    nodes.forEach(node => {
      const isHovered = hoveredNode === node.id;
      const isDragged = draggedNode === node.id;
      const nodeRadius = (isHovered || isDragged) ? 28 : 24;

      // Node circle
      ctx.beginPath();
      ctx.arc(node.x, node.y, nodeRadius, 0, 2 * Math.PI);
      ctx.fillStyle = node.type === 'document' ? '#3b82f6' : '#4ade80';
      ctx.fill();
      ctx.strokeStyle = isDragged ? '#fbbf24' : (isHovered ? '#ffffff' : '#1f2937');
      ctx.lineWidth = (isHovered || isDragged) ? 3 / zoom : 2 / zoom;
      ctx.stroke();

      // Node label
      ctx.fillStyle = '#e5e7eb';
      const fontSize = (isHovered || isDragged) ? 11 : 10;
      ctx.font = `${(isHovered || isDragged) ? 'bold' : 'normal'} ${fontSize}px system-ui`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      
      // Truncate label if too long
      let label = node.label;
      if (label.length > 12) {
        label = label.substring(0, 10) + '...';
      }
      
      // Draw label below the node
      ctx.fillText(label, node.x, node.y + nodeRadius + 12);
    });

    // Restore context
    ctx.restore();

  }, [nodes, edges, hoveredNode, draggedNode, zoom, pan]);

  const screenToCanvas = (screenX, screenY) => {
    return {
      x: (screenX - pan.x) / zoom,
      y: (screenY - pan.y) / zoom,
    };
  };

  const getNodeAtPosition = (x, y) => {
    const canvasPos = screenToCanvas(x, y);
    for (const node of nodes) {
      const dx = canvasPos.x - node.x;
      const dy = canvasPos.y - node.y;
      const distance = Math.sqrt(dx * dx + dy * dy);
      if (distance <= 24) {
        return node;
      }
    }
    return null;
  };

  const handleMouseDown = (e) => {
    if (!canvasRef.current) return;

    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const node = getNodeAtPosition(x, y);
    if (node) {
      const canvasPos = screenToCanvas(x, y);
      setDraggedNode(node.id);
      setDragOffset({
        x: canvasPos.x - node.x,
        y: canvasPos.y - node.y,
      });
    }
  };

  const handleMouseMove = (e) => {
    if (!canvasRef.current) return;

    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    // If dragging, update node position
    if (draggedNode) {
      const canvasPos = screenToCanvas(x, y);
      setNodes(prevNodes => 
        prevNodes.map(node => 
          node.id === draggedNode
            ? { ...node, x: canvasPos.x - dragOffset.x, y: canvasPos.y - dragOffset.y }
            : node
        )
      );
    } else {
      // Check if mouse is over any node for hover effect
      const node = getNodeAtPosition(x, y);
      setHoveredNode(node ? node.id : null);
    }
  };

  const handleMouseUp = () => {
    setDraggedNode(null);
  };

  const handleWheel = (e) => {
    e.preventDefault();
    
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    // Calculate zoom
    const delta = -e.deltaY;
    const zoomFactor = delta > 0 ? 1.1 : 0.9;
    const newZoom = Math.max(0.3, Math.min(3, zoom * zoomFactor));

    // Zoom towards mouse position
    const zoomRatio = newZoom / zoom;
    const newPan = {
      x: mouseX - (mouseX - pan.x) * zoomRatio,
      y: mouseY - (mouseY - pan.y) * zoomRatio,
    };

    setZoom(newZoom);
    setPan(newPan);
  };

  const handleZoomIn = () => {
    setZoom(prevZoom => Math.min(3, prevZoom * 1.2));
  };

  const handleZoomOut = () => {
    setZoom(prevZoom => Math.max(0.3, prevZoom / 1.2));
  };

  const handleResetZoom = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  if (!relationshipsData && !neighborsData) {
    return (
      <div className="graph-viz-empty">
        <p className="helper-text">
          Click "Get Relationships" above to visualize the graph.
        </p>
      </div>
    );
  }

  return (
    <div className="graph-viz-container">
      <div className="graph-viz-controls">
        <button className="zoom-btn" onClick={handleZoomIn} title="Zoom In">
          +
        </button>
        <button className="zoom-btn" onClick={handleZoomOut} title="Zoom Out">
          −
        </button>
        <button className="zoom-btn reset-btn" onClick={handleResetZoom} title="Reset Zoom">
          ↺
        </button>
        <span className="zoom-level">{Math.round(zoom * 100)}%</span>
      </div>
      <canvas
        ref={canvasRef}
        width={380}
        height={400}
        className="graph-viz-canvas"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onWheel={handleWheel}
        onMouseLeave={() => {
          setHoveredNode(null);
          setDraggedNode(null);
        }}
      />
      <div className="graph-viz-legend">
        <div className="legend-item">
          <div className="legend-circle document"></div>
          <span>Document</span>
        </div>
        <div className="legend-item">
          <div className="legend-circle entity"></div>
          <span>Entity</span>
        </div>
      </div>
    </div>
  );
}

export default App;
