apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  name: ${USER_NAME}-${SERVICE_NAME}-ingress
  namespace: ${NAMESPACE}
spec:
  ingressClassName: public-nginx
  rules:
  - host: data.yaxim.skala25a.project.skala-ai.com
    http:
      paths:
      - backend:
          service:
            name: ${USER_NAME}-${SERVICE_NAME}
            port:
              number: ${CONTAINER_PORT}
        path: /
        pathType: Prefix
  tls:
  - hosts:
    - data.yaxim.skala25a.project.skala-ai.com
    secretName: ${USER_NAME}-${SERVICE_NAME}-tls-secret
