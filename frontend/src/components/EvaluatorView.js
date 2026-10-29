import React, { useState, useEffect } from 'react';

function EvaluatorView() {
  const [evaluations, setEvaluations] = useState([]);
  const [activeStatusFilter, setActiveStatusFilter] = useState('ALL');
  const [isLiveConnected, setIsLiveConnected] = useState(false);

  useEffect(() => {
    // Connect to Server-Sent Events stream for instant evaluator push updates
    const eventSource = new EventSource('/api/events/subscribe');

    eventSource.onopen = () => {
      setIsLiveConnected(true);
    };

    eventSource.addEventListener('status_update', (event) => {
      try {
        const update = JSON.parse(event.data);
        setEvaluations((prev) => {
          const existingIndex = prev.findIndex((e) => e.applicationId === update.applicationId);
          if (existingIndex !== -1) {
            const updatedList = [...prev];
            updatedList[existingIndex] = {
              ...updatedList[existingIndex],
              status: update.status,
              complianceScore: update.complianceScore ?? updatedList[existingIndex].complianceScore,
              lastUpdated: new Date().toLocaleTimeString()
            };
            return updatedList;
          }
          return [
            {
              applicationId: update.applicationId,
              documentId: update.documentId,
              status: update.status,
              complianceScore: update.complianceScore ?? null,
              lastUpdated: new Date().toLocaleTimeString()
            },
            ...prev
          ];
        });
      } catch (err) {
        console.error('Error parsing evaluator event:', err);
      }
    });

    eventSource.onerror = () => {
      setIsLiveConnected(false);
    };

    return () => {
      eventSource.close();
    };
  }, []);

  const filteredEvaluations = evaluations.filter((item) => {
    if (activeStatusFilter === 'ALL') return true;
    return (item.status || '').toLowerCase() === activeStatusFilter.toLowerCase();
  });

  return (
    <div style={{ padding: '24px', fontFamily: 'system-ui, sans-serif' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '24px' }}>Evaluator Review Console</h1>
          <p style={{ margin: '4px 0 0', color: '#6b7280' }}>
            Live Queue Synchronization & Real-time AICTE Document Validation Stream
          </p>
        </div>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '6px 12px',
          borderRadius: '20px',
          backgroundColor: isLiveConnected ? '#f0fdf4' : '#fef2f2',
          border: `1px solid ${isLiveConnected ? '#bbf7d0' : '#fecaca'}`,
          fontSize: '13px',
          color: isLiveConnected ? '#166534' : '#991b1b'
        }}>
          <span style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            backgroundColor: isLiveConnected ? '#22c55e' : '#ef4444'
          }} />
          {isLiveConnected ? 'SSE Queue Live' : 'Disconnected'}
        </div>
      </div>

      {/* Filter Tabs */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
        {['ALL', 'Submitted', 'Under AI Review', 'Approved', 'Rejected'].map((status) => (
          <button
            key={status}
            onClick={() => setActiveStatusFilter(status)}
            style={{
              padding: '6px 14px',
              borderRadius: '6px',
              border: '1px solid #d1d5db',
              backgroundColor: activeStatusFilter === status ? '#1f2937' : '#ffffff',
              color: activeStatusFilter === status ? '#ffffff' : '#374151',
              cursor: 'pointer',
              fontWeight: 500,
              fontSize: '13px'
            }}
          >
            {status}
          </button>
        ))}
      </div>

      {/* Evaluation Stream Table */}
      <div style={{ border: '1px solid #e5e7eb', borderRadius: '8px', overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '14px' }}>
          <thead style={{ backgroundColor: '#f9fafb', borderBottom: '1px solid #e5e7eb' }}>
            <tr>
              <th style={{ padding: '12px 16px', color: '#4b5563', fontWeight: 600 }}>Application ID</th>
              <th style={{ padding: '12px 16px', color: '#4b5563', fontWeight: 600 }}>Status</th>
              <th style={{ padding: '12px 16px', color: '#4b5563', fontWeight: 600 }}>Compliance Score</th>
              <th style={{ padding: '12px 16px', color: '#4b5563', fontWeight: 600 }}>Last Updated</th>
            </tr>
          </thead>
          <tbody>
            {filteredEvaluations.length === 0 ? (
              <tr>
                <td colSpan="4" style={{ padding: '24px', textAlign: 'center', color: '#9ca3af' }}>
                  No applications in queue. Waiting for real-time evaluations from FastAPI service...
                </td>
              </tr>
            ) : (
              filteredEvaluations.map((item, idx) => (
                <tr key={idx} style={{ borderBottom: '1px solid #f3f4f6' }}>
                  <td style={{ padding: '12px 16px', fontFamily: 'monospace', fontWeight: 600 }}>{item.applicationId}</td>
                  <td style={{ padding: '12px 16px' }}>
                    <span style={{
                      padding: '4px 8px',
                      borderRadius: '4px',
                      fontSize: '12px',
                      fontWeight: 500,
                      backgroundColor:
                        item.status === 'Approved' ? '#dcfce7' :
                        item.status === 'Under AI Review' ? '#fef3c7' :
                        item.status === 'Rejected' ? '#fee2e2' : '#f3f4f6',
                      color:
                        item.status === 'Approved' ? '#15803d' :
                        item.status === 'Under AI Review' ? '#b45309' :
                        item.status === 'Rejected' ? '#b91c1c' : '#374151'
                    }}>
                      {item.status}
                    </span>
                  </td>
                  <td style={{ padding: '12px 16px' }}>
                    {item.complianceScore !== null ? `${item.complianceScore}%` : 'Pending'}
                  </td>
                  <td style={{ padding: '12px 16px', color: '#6b7280' }}>{item.lastUpdated}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default EvaluatorView;
