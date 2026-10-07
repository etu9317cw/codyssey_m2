// 이 파일을 config.js 로 복사해 백엔드 주소를 넣는다. config.js 는 .gitignore 에 있다.
// 로컬:  http://localhost:8000      Render 배포: https://<서비스명>.onrender.com
window.APP_CONFIG = {
  API_BASE_URL: "http://localhost:8000",
  REQUEST_TIMEOUT_MS: 25000,   // Render 무료 티어 콜드스타트(최대 50초)를 고려해 채팅은 2배로 늘린다
};
