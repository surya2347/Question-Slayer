# Question-Slayer

NCS 자격증 학습을 위한 AI 기반 질의응답 플랫폼.
블룸의 분류학 기반 질문 수준 분석 + 6가지 관점 맞춤 답변 + 관심사 비유 학습.

## 실행 방법

```bash
# 1. 저장소 클론
git clone https://github.com/surya2347/Question-Slayer.git
cd Question-Slayer

# 2. 가상환경 생성 및 의존성 설치 (uv)
uv venv
uv sync
source .venv/bin/activate

# 3. 환경 변수 설정
cp .env.example .env
# .env 파일에 OPENAI_API_KEY 입력

# 4. 앱 실행
streamlit run app.py
```

## 팀
- 2인 팀 / 개발 기간: 7일
