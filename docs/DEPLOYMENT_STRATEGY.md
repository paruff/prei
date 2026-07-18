# Deployment Strategy — prei

> Current: Direct deployment to single instance.
> Target: Canary deployment with progressive traffic shifting.

---

## Current Architecture

```
git push main → docker-publish.yml → build + publish
                  → post-deployment.yml: smoke + acceptance + performance + security
                  → deploy to single instance (Render/Docker)
```

**Limitations:** No progressive rollout. Any failure affects 100% of traffic. No automated rollback based on metrics.

---

## Target Architecture (Canary)

```
git push main → docker-publish.yml → build + publish
                  → deploy to CANARY (5% traffic)
                  → monitor for 5 min:
                     ├── health OK + error rate < 1% → promote to 100%
                     └── health FAIL or error rate > 1% → rollback canary
                  → post-deployment.yml validates stable
```

### Prerequisites

| Component | Requirement |
|---|---|
| Orchestrator | Kubernetes (GKE/EKS/AKS) or Render with traffic splitting |
| Replicas | ≥ 2 identical replicas |
| Load Balancer | Nginx ingress or cloud LB with traffic weights |
| Monitoring | Prometheus + Grafana or cloud-native equivalent |
| CI Integration | GitHub Actions with kubectl/helm access |

### Canary Flow

```
Step 1: Deploy new image to canary namespace/replicaset
        kubectl set image deployment/prei-canary app=$NEW_IMAGE
        kubectl scale deployment/prei-canary --replicas=1

Step 2: Route 5% traffic to canary
        kubectl patch ingress prei -p '{"metadata":{"annotations":{"nginx.ingress.kubernetes.io/canary":"true","nginx.ingress.kubernetes.io/canary-weight":"5"}}}'

Step 3: Monitor for 5 minutes
        while [ $SECONDS -lt 300 ]; do
          STATUS=$(curl -s -o /dev/null -w "%{http_code}" $CANARY_URL/health/)
          if [ "$STATUS" != "200" ]; then ROLLBACK=1; break; fi
          sleep 10
        done

Step 4: Promote or rollback
        if [ "$ROLLBACK" = "1" ]; then
          kubectl scale deployment/prei-canary --replicas=0  # rollback
        else
          kubectl set image deployment/prei-stable app=$NEW_IMAGE  # promote
          kubectl scale deployment/prei-canary --replicas=0
        fi
```

### Rollback Triggers

| Trigger | Threshold | Action |
|---|---|---|
| Health check failure | 3 consecutive 5xx | Rollback immediately |
| Error rate spike | > 1% of requests | Rollback after 60s |
| P99 latency | > 500ms for 2 min | Investigate, manual decision |
| User-reported bug | Any critical bug | Rollback immediately |

### Manual Override

```bash
# Promote immediately: kubectl set image deployment/prei-stable app=$NEW_IMAGE
# Rollback immediately: kubectl scale deployment/prei-canary --replicas=0
```

---

## Migration Path

1. **Deploy K8s cluster** (GKE autopilot for minimal ops overhead)
2. **Migrate from single-instance Docker to K8s deployment**
3. **Configure ingress with canary annotations**
4. **Add canary deploy step to docker-publish.yml**
5. **Add Prometheus metrics for error rate + latency**
6. **Automate promote/rollback decisions in CI**

---

## Interim (Pre-K8s) Safety

Until K8s is available, the post-deployment pipeline serves as the deploy gate:
- Smoke tests run within seconds of deploy
- Acceptance tests verify content within 60s
- Rollback is triggered manually or via the post-deployment rollback job
