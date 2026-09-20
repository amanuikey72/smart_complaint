/* -------------------------------------------------------------------
   SmartComplaint AI — Live AI Real-Time Analyzer Handler
------------------------------------------------------------------- */

document.addEventListener('DOMContentLoaded', () => {
  const titleInput = document.getElementById('complaintTitle');
  const descInput = document.getElementById('complaintDesc');
  const catSelect = document.getElementById('complaintCategory');

  if (!titleInput || !descInput) return;

  let debounceTimer = null;

  const triggerLiveAnalysis = () => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      runAIAnalysis();
    }, 300);
  };

  titleInput.addEventListener('input', triggerLiveAnalysis);
  descInput.addEventListener('input', triggerLiveAnalysis);
  if (catSelect) catSelect.addEventListener('change', triggerLiveAnalysis);

  if (titleInput.value.trim() || descInput.value.trim()) {
    runAIAnalysis();
  }
});

async function runAIAnalysis() {
  const title = document.getElementById('complaintTitle').value.trim();
  const description = document.getElementById('complaintDesc').value.trim();
  const category = document.getElementById('complaintCategory')?.value || '';

  const aiStatus = document.getElementById('aiStatusText');

  if (!title && !description) {
    resetAIPanelToPlaceholder();
    return;
  }

  if (aiStatus) {
    aiStatus.textContent = 'ANALYZING LANGUAGE...';
    aiStatus.style.color = 'var(--accent-copper)';
  }

  try {
    const response = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, description, category })
    });

    if (!response.ok) throw new Error(`API Error: ${response.status}`);

    const data = await response.json();
    updateAIPanelUI(data);

  } catch (error) {
    console.error('AI Analysis failed:', error);
    if (aiStatus) {
      aiStatus.textContent = 'ANALYSIS TEMPORARILY OFFLINE';
      aiStatus.style.color = 'var(--status-critical)';
    }
  }
}

function updateAIPanelUI(data) {
  const scoreElem = document.getElementById('aiScoreValue');
  const badgeElem = document.getElementById('aiPriorityBadge');
  const categoryElem = document.getElementById('aiCategoryVal');
  const urgencyElem = document.getElementById('aiUrgencyVal');
  const riskElem = document.getElementById('aiRiskVal');
  const handlingElem = document.getElementById('aiHandlingVal');
  const signalsContainer = document.getElementById('aiDetectedSignals');
  const explanationContainer = document.getElementById('aiExplanationList');
  const aiStatus = document.getElementById('aiStatusText');

  if (aiStatus) {
    aiStatus.textContent = 'EVALUATION COMPLETE';
    aiStatus.style.color = 'var(--color-ivory)';
  }

  if (scoreElem) {
    scoreElem.textContent = `${data.score} / 100`;
  }

  if (badgeElem) {
    let statusClass = 'status-low';
    if (data.priority === 'CRITICAL') statusClass = 'status-critical';
    else if (data.priority === 'HIGH') statusClass = 'status-high';
    else if (data.priority === 'MEDIUM') statusClass = 'status-medium';

    badgeElem.className = `status-tag ${statusClass}`;
    badgeElem.textContent = data.priority;
  }

  if (categoryElem) categoryElem.textContent = data.category;
  if (urgencyElem) urgencyElem.textContent = data.urgency;
  if (riskElem) riskElem.textContent = data.risk_level;
  if (handlingElem) handlingElem.textContent = data.recommended_handling;

  if (signalsContainer) {
    signalsContainer.innerHTML = '';
    const signals = data.detected_signals || [];
    if (signals.length === 0) {
      signalsContainer.textContent = 'Standard text signals';
      signalsContainer.style.color = 'var(--text-dim)';
    } else {
      signals.forEach(signal => {
        const tag = document.createElement('span');
        tag.className = 'status-tag status-pending';
        tag.style.marginRight = '0.35rem';
        tag.style.marginBottom = '0.35rem';
        tag.textContent = signal;
        signalsContainer.appendChild(tag);
      });
    }
  }

  if (explanationContainer) {
    explanationContainer.innerHTML = '';
    const factors = data.explanation_factors || [];
    if (factors.length === 0) {
      explanationContainer.textContent = 'None';
      explanationContainer.style.color = 'var(--text-dim)';
    } else {
      factors.forEach(factor => {
        const item = document.createElement('div');
        item.style.cssText = 'font-family: var(--font-mono); font-size: 0.78rem; color: var(--text-muted); margin-bottom: 0.4rem; display: flex; align-items: flex-start; gap: 0.5rem;';
        item.innerHTML = `<span style="color: var(--accent-copper)">✓</span> <span>${factor}</span>`;
        explanationContainer.appendChild(item);
      });
    }
  }
}

function resetAIPanelToPlaceholder() {
  const scoreElem = document.getElementById('aiScoreValue');
  const badgeElem = document.getElementById('aiPriorityBadge');
  const categoryElem = document.getElementById('aiCategoryVal');
  const urgencyElem = document.getElementById('aiUrgencyVal');
  const signalsContainer = document.getElementById('aiDetectedSignals');
  const explanationContainer = document.getElementById('aiExplanationList');
  const aiStatus = document.getElementById('aiStatusText');

  if (scoreElem) scoreElem.textContent = '0 / 100';
  if (badgeElem) {
    badgeElem.className = 'status-tag status-low';
    badgeElem.textContent = 'LOW';
  }
  if (categoryElem) categoryElem.textContent = '—';
  if (urgencyElem) urgencyElem.textContent = '—';
  if (signalsContainer) signalsContainer.textContent = '—';
  if (explanationContainer) explanationContainer.textContent = '—';

  if (aiStatus) {
    aiStatus.textContent = 'AWAITING INPUT...';
    aiStatus.style.color = 'var(--text-dim)';
  }
}
