# backend 이미지 빌드
docker build -t hyunjun-backend:latest ./backend
# frontend 이미지 빌드
docker build -t hyunjun-frontend:latest ./frontend

# k8s 리소스 삭제
kubectl delete -f k8s

# k8s 리소스 적용
kubectl apply -f k8s

sleep 5

kubectl port-forward deployment/frontend -n hyunjun 8080:80