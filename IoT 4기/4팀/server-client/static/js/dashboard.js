/* static/js/dashboard.js */

// Unity WebGL 로더 설정
var buildUrl = "/static/Build";
var loaderUrl = buildUrl + "/Cart_Project.loader.js";
var config = {
    dataUrl: buildUrl + "/Cart_Project.data.unityweb",
    frameworkUrl: buildUrl + "/Cart_Project.framework.js.unityweb",
    codeUrl: buildUrl + "/Cart_Project.wasm.unityweb",
    streamingAssetsUrl: "StreamingAssets",
    companyName: "DefaultCompany",
    productName: "WebGL Test3",
    productVersion: "0.1.0",
};

// ★ [핵심] 대시보드 기능을 관리하는 클래스 정의
class CartDashboard {
    constructor() {
        this.socket = io();
        this.unityInstance = null;
        
        // 상태 변수
        this.isShoppingStarted = false;
        this.isShoppingEnded = false;
        this.isCartView = false;
        
        // 타이머 및 거리 계산 변수
        this.startTime = 0;
        this.timerInterval = null;
        // this.totalDistance = 0.0;
        this.prevX = null;
        this.prevY = null;

        // 종료 구역 설정
        this.EXIT_ZONE = { minX: 0.0, maxX: 1.2, minY: 0, maxY: 1.2 };

        // 초기화 실행
        this.initSocketEvents();
        this.initUnity();
    }

    // 1. 소켓 이벤트 설정
    initSocketEvents() {
        this.socket.on('connect', () => {
            document.getElementById("netStatus").innerHTML = '<span style="color:#0f0">● Online</span>';
        });

        this.socket.on('sc_data', (msg) => this.handleData(msg));
    }

    // 2. Unity 초기화 및 로드
    initUnity() {
        const canvas = document.querySelector("#unity-canvas");
        const script = document.createElement("script");
        script.src = loaderUrl;
        
        script.onload = () => {
            createUnityInstance(canvas, config, (progress) => {
                document.querySelector("#unity-progress-bar-full").style.width = 100 * progress + "%";
            }).then((instance) => {
                this.unityInstance = instance; // 클래스 멤버변수에 저장
                document.querySelector("#unity-loading-bar").style.display = "none";
            }).catch((message) => {
                alert(message);
            });
        };
        document.body.appendChild(script);
    }

    // 3. 데이터 수신 시 처리 로직
    handleData(msg) {
        if (this.isShoppingEnded) return;

        const currentX = typeof msg.x === 'number' ? msg.x : parseFloat(msg.x);
        const currentY = typeof msg.y === 'number' ? msg.y : parseFloat(msg.y);
        const rawAngle = msg.angle;

        // // 거리 계산
        // this.calculateDistance(currentX, currentY);

        // Unity로 전송
        this.sendToUnity(currentX, currentY, rawAngle);

        // HTML UI 업데이트
        this.updateUI(currentX, currentY, rawAngle);

        // 종료 구역 체크
        this.checkExitZone(currentX, currentY);

        // 타이머 시작 체크
        if (!this.isShoppingStarted) {
            this.startTimer();
        }
    }

    sendToUnity(x, y, rawAngle) {
        if (this.unityInstance) {
            const unityAngle = (rawAngle - 90 + 360) % 360;
            const unityData = { x: x, y: y, angle: unityAngle };
            this.unityInstance.SendMessage("GameManager", "ReceiveWebData", JSON.stringify(unityData));
        }
    }

    updateUI(x, y, angle) {
        document.getElementById("dispX").innerText = x.toFixed(2);
        document.getElementById("dispY").innerText = y.toFixed(2);
        document.getElementById("dispAngle").innerText = angle;
        // document.getElementById("dispDist").innerText = this.totalDistance.toFixed(2);
    }

    checkExitZone(x, y) {
        if (this.isShoppingEnded) return;

        const btnEnd = document.getElementById("btnEnd");
        const isInZone = (x >= this.EXIT_ZONE.minX && x <= this.EXIT_ZONE.maxX) &&
                         (y >= this.EXIT_ZONE.minY && y <= this.EXIT_ZONE.maxY);

        if (isInZone) {
            btnEnd.disabled = false;
            btnEnd.innerText = "🛑 쇼핑 종료 (가능)";
            btnEnd.style.opacity = "1";
        } else {
            btnEnd.disabled = true;
            btnEnd.innerText = "🛑 계산대로 이동해주세요";
            btnEnd.style.opacity = "0.5";
        }
    }

    startTimer() {
        this.isShoppingStarted = true;
        this.startTime = Date.now();
        this.timerInterval = setInterval(() => {
            const now = Date.now();
            const diff = now - this.startTime;
            const seconds = Math.floor((diff / 1000) % 60);
            const minutes = Math.floor((diff / (1000 * 60)) % 60);
            const hours = Math.floor(diff / (1000 * 60 * 60));
            
            const timeStr = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
            document.getElementById("timer-display").innerText = timeStr;
        }, 1000);
    }

    // [외부 호출용 함수] 쇼핑 종료
    endShopping() {
        if (this.isShoppingEnded) return;
        
        this.isShoppingEnded = true;
        if (this.timerInterval) clearInterval(this.timerInterval);

        console.log("🚫 쇼핑 종료! 결과 화면으로 이동합니다.");

        // 복잡한 소켓 통신 없이 바로 결과 페이지로 이동합니다.
        // 현재 쇼핑은 끝났으니, 결과 페이지에서 다시 시작할 때 ID를 올리면 됩니다.
        window.location.href = "/shoppingEnd";
    }

    // [외부 호출용 함수] 카메라 전환
    toggleCamera() {
        if (!this.unityInstance) return;
        this.isCartView = !this.isCartView;
        this.unityInstance.SendMessage("GameManager", "SwitchView", this.isCartView.toString());

        const btn = document.getElementById("btnCam");
        if (this.isCartView) {
            btn.innerText = "🛒 카트 시점 (클릭하여 복귀)";
            btn.classList.add("active");
        } else {
            btn.innerText = "📹 CCTV 시점 보기";
            btn.classList.remove("active");
        }
    }
}

// 페이지 로드 시 인스턴스 생성
let dashboard;
window.onload = () => {
    dashboard = new CartDashboard();
};