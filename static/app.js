const form = document.querySelector("#recommend-form");
const output = document.querySelector("#output");
const advisor = document.querySelector("#advisor");
const submitButton = document.querySelector("#submit-button");
const errorBox = document.querySelector("#form-error");
const won = new Intl.NumberFormat("ko-KR");
let currentCustomer = null;

const priorityLabels = {
  highest_interest: "실현 가능한 예상이자를 가장 크게 반영했습니다.",
  easy_conditions: "금리와 함께 우대조건의 간편성을 반영했습니다.",
  liquidity: "금리와 함께 분할해지·비상금 출금 등 자금 활용 편의를 반영했습니다.",
  inclusive: "금리와 함께 확인된 포용금융 지원 자격을 반영했습니다."
};

const presets = {
  young: {
    age: 29, amount: 10000000, term_months: 12, channel: "online",
    priority: "highest_interest", salary_or_pension: true,
    first_term_deposit: true, auto_renew: true
  },
  senior: {
    age: 68, amount: 50000000, term_months: 12, channel: "online",
    priority: "easy_conditions", salary_or_pension: true,
    checking_balance: 1000000, auto_renew: true
  },
  business: {
    age: 47, amount: 80000000, term_months: 12, channel: "branch",
    priority: "inclusive", business_owner: true, yellow_umbrella: true,
    checking_balance: 3000000
  },
  rural: {
    age: 58, amount: 5000000, term_months: 12, channel: "branch",
    priority: "inclusive", vulnerable_or_rural: true, government_support: true
  }
};

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formValues() {
  const data = {};
  new FormData(form).forEach((value, key) => { data[key] = value; });
  form.querySelectorAll('input[type="checkbox"]').forEach(input => {
    data[input.name] = input.checked;
  });
  [
    "age", "amount", "term_months", "checking_balance", "card_spend",
    "referral_count", "automatic_transfers"
  ].forEach(key => { data[key] = Number(data[key] || 0); });
  return data;
}

function setPreset(name) {
  form.reset();
  form.querySelectorAll('input[type="checkbox"]').forEach(input => {
    input.checked = false;
  });
  form.querySelector('[name="paperless"]').checked = true;
  const preset = presets[name];
  Object.entries(preset).forEach(([key, value]) => {
    const input = form.elements.namedItem(key);
    if (!input) return;
    if (input.type === "checkbox") input.checked = Boolean(value);
    else input.value = value;
  });
  form.requestSubmit();
}

function signedMoney(value) {
  const sign = value > 0 ? "+" : "";
  return `${sign}${won.format(value)}원`;
}

function renderResults(data) {
  const top = data.recommendations[0];
  if (!top) {
    throw new Error("현재 조건으로 가입 가능한 상품이 없습니다. 가입기간이나 채널을 바꿔 주세요.");
  }
  const freshness = document.querySelector("#freshness");
  freshness.classList.toggle("stale", data.data_freshness.status !== "fresh");
  freshness.textContent = data.data_freshness.status === "fresh"
    ? `금리 기준일 ${data.rate_reference_date} · ${data.data_freshness.age_days}일 전 정보`
    : data.data_freshness.status === "warning"
      ? `확인 권장: 금리 정보가 ${data.data_freshness.age_days}일 지났습니다. 가입 전 최신 금리를 다시 확인하세요.`
      : `주의: 금리 정보가 ${data.data_freshness.age_days}일 지났습니다. 추천값보다 최신 상품설명서를 우선하세요.`;

  document.querySelector("#priority-description").textContent = priorityLabels[data.priority];
  document.querySelector("#summary").innerHTML = `
    <div class="metric"><span>가입 가능 상품</span><strong>${data.comparison.full_candidate_count}개</strong></div>
    <div class="metric"><span>1위 실현 가능 금리</span><strong>연 ${top.achievable_rate.toFixed(2)}%</strong></div>
    <div class="metric"><span>일반과세 예상 세후이자</span><strong>${won.format(top.net_interest)}원</strong></div>
    <div class="metric"><span>기존 추천 대비 세전이자 차이</span><strong>${signedMoney(data.comparison.interest_difference)}</strong></div>`;

  document.querySelector("#results").innerHTML = data.recommendations.map(item => {
    const conditions = item.matched_conditions.length
      ? item.matched_conditions.map(text => `<span class="tag">${escapeHtml(text)}</span>`).join("")
      : '<span class="tag">기본금리 적용</span>';
    const next = item.next_actions.length
      ? `추가 확인: ${item.next_actions.map(action =>
          `${escapeHtml(action.label)}(+${action.additional_rate.toFixed(2)}%p)`
        ).join(", ")}`
      : "현재 확인된 조건으로 상품 우대상한을 모두 반영했습니다.";
    const inclusive = item.inclusion.matched
      ? `<span class="inclusive-badge">포용금융 적합</span>`
      : "";
    return `
      <article class="card">
        <div class="rank" aria-label="${item.rank}위">${item.rank}</div>
        <div>
          <h3>${escapeHtml(item.name)}${inclusive}</h3>
          <p class="card-description">${escapeHtml(item.description)}</p>
          <div class="tags" aria-label="반영된 우대조건">${conditions}</div>
          <p class="next-action">${next}</p>
          <p class="score-note">추천점수 ${item.recommendation_score.toFixed(1)} · 기본 ${item.base_rate.toFixed(2)}% + 반영 우대 ${item.applied_bonus.toFixed(2)}%p</p>
        </div>
        <div class="rate">
          <strong>연 ${item.achievable_rate.toFixed(2)}%</strong>
          <span>세전 ${won.format(item.gross_interest)}원</span>
          <span>세후 약 ${won.format(item.net_interest)}원</span>
          <a href="${escapeHtml(item.source_url)}" target="_blank" rel="noopener noreferrer">공식 상품정보</a>
        </div>
      </article>`;
  }).join("");

  output.hidden = false;
  advisor.hidden = false;
  output.scrollIntoView({behavior: "smooth", block: "start"});
}

async function requestRecommendation() {
  errorBox.hidden = true;
  submitButton.disabled = true;
  submitButton.textContent = "전체 상품을 비교하고 있습니다";
  currentCustomer = formValues();
  try {
    const response = await fetch("/api/recommend", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(currentCustomer)
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "추천 결과를 불러오지 못했습니다.");
    renderResults(data);
    document.querySelector("#answer-box").hidden = true;
    document.querySelectorAll(".question-button").forEach(button => {
      button.setAttribute("aria-pressed", "false");
    });
  } catch (error) {
    errorBox.textContent = error.message;
    errorBox.hidden = false;
    output.hidden = true;
    advisor.hidden = true;
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = "전체 상품 비교하기";
  }
}

async function loadQuestions() {
  const response = await fetch("/api/advice/questions");
  const data = await response.json();
  document.querySelector("#question-grid").innerHTML = data.questions.map(question =>
    `<button type="button" class="question-button" data-question="${escapeHtml(question.id)}" aria-pressed="false">${escapeHtml(question.label)}</button>`
  ).join("");
}

async function askAdvisor(button) {
  if (!currentCustomer) return;
  document.querySelectorAll(".question-button").forEach(item => {
    item.setAttribute("aria-pressed", String(item === button));
    item.disabled = true;
  });
  const answerBox = document.querySelector("#answer-box");
  const answerText = document.querySelector("#answer-text");
  answerBox.hidden = false;
  answerText.textContent = "상품정보에서 관련 근거를 찾고 있습니다.";
  document.querySelector("#answer-sources").innerHTML = "";
  try {
    const response = await fetch("/api/advice", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        question_id: button.dataset.question,
        customer: currentCustomer
      })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "답변을 불러오지 못했습니다.");
    answerText.textContent = data.answer;
    document.querySelector("#answer-sources").innerHTML = data.citations.length
      ? `<strong>확인한 근거</strong><ul class="source-list">${data.citations.map(source =>
          `<li><a href="${escapeHtml(source.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(source.title)}</a> · ${escapeHtml(source.detail)}</li>`
        ).join("")}</ul>`
      : "";
  } catch (error) {
    answerText.textContent = error.message;
  } finally {
    document.querySelectorAll(".question-button").forEach(item => { item.disabled = false; });
  }
}

form.addEventListener("submit", event => {
  event.preventDefault();
  requestRecommendation();
});

document.querySelectorAll(".preset").forEach(button => {
  button.addEventListener("click", () => setPreset(button.dataset.preset));
});

document.querySelector("#question-grid").addEventListener("click", event => {
  const button = event.target.closest(".question-button");
  if (button) askAdvisor(button);
});

document.querySelector("#font-toggle").addEventListener("click", event => {
  const pressed = event.currentTarget.getAttribute("aria-pressed") === "true";
  event.currentTarget.setAttribute("aria-pressed", String(!pressed));
  document.body.classList.toggle("large-text", !pressed);
});

document.querySelector("#contrast-toggle").addEventListener("click", event => {
  const pressed = event.currentTarget.getAttribute("aria-pressed") === "true";
  event.currentTarget.setAttribute("aria-pressed", String(!pressed));
  document.body.classList.toggle("high-contrast", !pressed);
});

loadQuestions().then(() => form.requestSubmit()).catch(error => {
  errorBox.textContent = error.message;
  errorBox.hidden = false;
});
