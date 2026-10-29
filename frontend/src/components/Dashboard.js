import React, { useState, useEffect } from 'react';

const STATUS_STEPS = [
  { id: 'draft', label: 'Draft', description: 'Application initiated' },
  { id: 'submitted', label: 'Submitted', description: 'Institutional submission complete' },
  { id: 'under_ai_review', label: 'Under AI Review', description: 'ML extraction & compliance verification' },
  { id: 'approved', label: 'Approved', description: 'Final evaluator clearance' }
];

function Dashboard({ applicationId }) {
  const [currentStatus, setCurrentStatus] = useState('draft');
  const [complianceScore, setComplianceScore] = useState(null);
  const [eventLogs, setEventLogs] = useState([]);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    // Connect to Server-Sent Events stream for real-time status updates (Issue #118, #32)
    const eventSource = new EventSource('/api/events/subscribe');

    eventSource.onopen = () => {
      setIsConnected(true);
    };

    eventSource.addEventListener('status_update', (event) => {
      try {
        const data = JSON.parse(event.data);
        if (!applicationId || data.applicationId === applicationId) {
          // Normalize status
          const normalized = (data.status || '').toLowerCase().replace(/\s+/g, '_');
          setCurrentStatus(normalized);

          if (data.complianceScore !== undefined) {
            setComplianceScore(data.complianceScore);
          }

          setEventLogs((prev) => [
            {
              id: Date.now(),
              time: new Date(data.timestamp || Date.now()).toLocaleTimeString(),
              status: data.status,
              message: data.message || `Status updated to ${data.status}`
            },
            ...prev.slice(0, 9)
          ]);
        }
      } catch (err) {
        console.error('Failed to parse SSE event:', err);
      }
    });

    eventSource.onerror = () => {
      setIsConnected(false);
    };

    return () => {
      eventSource.close();
    };
  }, [applicationId]);

  const getStepClass = (stepId, index) => {
    const statusOrder = ['draft', 'submitted', 'under_ai_review', 'approved'];
    const currentIndex = statusOrder.indexOf(currentStatus);
    const stepIndex = statusOrder.indexOf(stepId);

    if (currentStatus === 'rejected' && stepId === 'approved') return 'step-failed';
    if (stepIndex <= currentIndex && currentIndex !== -1) return 'step-completed';
    return 'step-pending';
  };

  return (
    <div style={{ padding: '24px', fontFamily: 'system-ui, sans-serif' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h1 style={{ margin: 0 }}>Application Dashboard</h1>
          <p style={{ margin: '4px 0 0', color: '#6b7280' }}>
            Real-time Institutional Evaluation & Status Tracking
          </p>
        </div>
        <div>
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            padding: '6px 12px',
            borderRadius: '16px',
            fontSize: '13px',
            fontWeight: 500,
            backgroundColor: isConnected ? '#dcfce7' : '#fee2e2',
            color: isConnected ? '#15803d' : '#b91c1c'
          }}>
            <span style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: isConnected ? '#22c55e' : '#ef4444',
              marginRight: '8px'
            }} />
            {isConnected ? 'Live Sync Active' : 'Connecting to Stream...'}
          </span>
        </div>
      </header>

      {/* Real-time Status Progress Bar */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: '12px',
        margin: '24px 0',
        padding: '20px',
        backgroundColor: '#f9fafb',
        borderRadius: '12px',
        border: '1px solid #e5e7eb'
      }}>
        {STATUS_STEPS.map((step, idx) => (
          <div
            key={step.id}
            style={{
              padding: '12px',
              borderRadius: '8px',
              backgroundColor: '#fff',
              border: `2px solid ${getStepClass(step.id, idx) === 'step-completed' ? '#2563eb' : '#e5e7eb'}`
            }}
          >
            <div style={{ fontSize: '12px', color: '#6b7280' }}>Stage 0{idx + 1}</div>
            <div style={{ fontSize: '15px', fontWeight: 600, color: '#111827', margin: '4px 0' }}>{step.label}</div>
            <div style={{ fontSize: '12px', color: '#4b5563' }}>{step.description}</div>
          </div>
        ))}
      </div>

      {complianceScore !== null && (
        <div style={{
          backgroundColor: '#eff6ff',
          border: '1px solid #bfdbfe',
          color: '#1e40af',
          padding: '16px',
          borderRadius: '8px',
          marginBottom: '20px'
        }}>
          <strong>AI Compliance Result: </strong> {complianceScore}% Institutional Adherence
        </div>
      )}

      {/* Live Event Stream Feed */}
      <section style={{ marginTop: '24px' }}>
        <h3 style={{ fontSize: '16px', fontWeight: 600, color: '#111827' }}>Live Event Feed (Redis & SSE)</h3>
        {eventLogs.length === 0 ? (
          <p style={{ color: '#9ca3af', fontSize: '14px' }}>Waiting for status transitions...</p>
        ) : (
          <ul style={{ listStyle: 'none', padding: 0 }}>
            {eventLogs.map((log) => (
              <li
                key={log.id}
                style={{
                  padding: '10px 14px',
                  marginBottom: '8px',
                  backgroundColor: '#ffffff',
                  border: '1px solid #e5e7eb',
                  borderRadius: '6px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  fontSize: '14px'
                }}
              >
                <span><strong>[{log.status}]</strong> {log.message}</span>
                <span style={{ color: '#9ca3af' }}>{log.time}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

export default Dashboard;
