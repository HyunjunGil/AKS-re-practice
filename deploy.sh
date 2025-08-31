# ACR 로그인
echo "ACR에 로그인 중..."
if ! az acr login --name ktech4; then
    echo "ACR 로그인 실패! 스크립트를 중단합니다."
    exit 1
fi
echo "ACR 로그인 성공!"

# backend 이미지 빌드 및 ACR에 푸시
docker build --platform linux/amd64 -t ktech4.azurecr.io/hyunjun-backend:latest ./backend

docker push ktech4.azurecr.io/hyunjun-backend:latest

# frontend 이미지 빌드 및 ACR에 푸시
docker build --platform linux/amd64 -t ktech4.azurecr.io/hyunjun-frontend:latest ./frontend
docker push ktech4.azurecr.io/hyunjun-frontend:latest

# k8s 리소스 삭제
kubectl delete -f k8s

# k8s 리소스 적용
kubectl apply -f k8s

sleep 5

kubectl port-forward deployment/hyunjun-frontend -n hyunjun 8080:80