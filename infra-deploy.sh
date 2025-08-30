helm uninstall mariadb -n infra
helm uninstall redis -n infra
helm uninstall kafka -n infra

helm install mariadb oci://registry-1.docker.io/bitnamicharts/mariadb -n infra -f charts/mariadb/values.yaml
helm install redis oci://registry-1.docker.io/bitnamicharts/redis -n infra -f charts/redis/values.yaml
helm install kafka oci://registry-1.docker.io/bitnamicharts/kafka -n infra -f charts/kafka/values.yaml
