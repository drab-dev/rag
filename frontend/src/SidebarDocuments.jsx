import React, { useCallback, useEffect, useState } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

function SidebarDocuments({ onStatsChange }) {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedDocId, setSelectedDocId] = useState(null);
  const [selectedDocPreview, setSelectedDocPreview] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [notification, setNotification] = useState(null);

  const clearNotificationLater = () => {
    if (!notification) return;
    setTimeout(() => setNotification(null), 3000);
  };

  useEffect(clearNotificationLater, [notification]);

  const loadDocuments = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/list_documents`);
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Failed to load documents (status ${res.status})`);
      }
      const data = await res.json();
      setDocuments(Array.isArray(data.documents) ? data.documents : []);
    } catch (e) {
      console.error(e);
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  const handleSelectDoc = async (docId) => {
    setSelectedDocId(docId);
    setSelectedDocPreview(null);
    setPreviewLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/document/${encodeURIComponent(docId)}`);
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Failed to load document (status ${res.status})`);
      }
      const data = await res.json();
      setSelectedDocPreview(data.document || '');
    } catch (e) {
      console.error(e);
      setSelectedDocPreview(null);
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleDelete = async (docId) => {
    // Simple confirmation to avoid accidental deletes
    /* eslint-disable no-alert */
    const confirmDelete = window.confirm(`Delete document "${docId}"? This cannot be undone.`);
    /* eslint-enable no-alert */
    if (!confirmDelete) return;

    try {
      const res = await fetch(`${API_BASE_URL}/document/${encodeURIComponent(docId)}`, {
        method: 'DELETE',
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Delete failed with status ${res.status}`);
      }
      const data = await res.json();
      console.debug('Delete result', data);
      setNotification({ type: 'success', text: `Deleted document ${docId}.` });
      // Refresh list and stats
      await loadDocuments();
      if (typeof onStatsChange === 'function') {
        onStatsChange();
      }
      if (selectedDocId === docId) {
        setSelectedDocId(null);
        setSelectedDocPreview(null);
      }
    } catch (e) {
      console.error(e);
      setNotification({
        type: 'error',
        text: e instanceof Error ? e.message : 'Failed to delete document.',
      });
    }
  };

  const renderPreviewSnippet = (text) => {
    if (!text) return '';
    if (text.length <= 220) return text;
    return `${text.slice(0, 220)}…`;
  };

  return (
    <section className="card sidebar-documents">
      <h2>Documents</h2>
      <p className="helper-text">
        Lists all document IDs via <code>GET /list_documents</code>. You can click a document to
        preview it or delete it.
      </p>

      {notification && (
        <p className={notification.type === 'error' ? 'error-text' : 'success-text'}>
          {notification.text}
        </p>
      )}

      {error && <p className="error-text">{error}</p>}

      <div className="sidebar-documents-list-wrapper">
        <div className="sidebar-documents-list-header">
          <span className="sidebar-documents-count">
            Total: {documents.length}
          </span>
          {loading && <span className="sidebar-documents-loading">Loading…</span>}
        </div>
        <ul className="sidebar-documents-list">
          {documents.map((docId) => (
            <li key={docId} className={docId === selectedDocId ? 'is-selected' : ''}>
              <button
                type="button"
                className="sidebar-documents-doc-button"
                onClick={() => handleSelectDoc(docId)}
              >
                <span className="sidebar-documents-doc-id">{docId}</span>
              </button>
              <button
                type="button"
                className="sidebar-documents-delete-button"
                onClick={() => handleDelete(docId)}
              >
                
                Delete
              </button>
            </li>
          ))}

          {!loading && documents.length === 0 && (
            <li className="sidebar-documents-empty">No documents yet. Add one on the left.</li>
          )}
        </ul>
      </div>

      <div className="sidebar-documents-preview">
        <div className="section-title-sm">Preview</div>
        {!selectedDocId && <p className="helper-text">Select a document to see a preview.</p>}
        {selectedDocId && previewLoading && (
          <p className="helper-text">Loading document {selectedDocId}…</p>
        )}
        {selectedDocId && !previewLoading && (
          <>
            <div className="meta-line">Doc ID: {selectedDocId}</div>
            <div className="snippet">{renderPreviewSnippet(selectedDocPreview)}</div>
          </>
        )}
      </div>
    </section>
  );
}

export default SidebarDocuments;
