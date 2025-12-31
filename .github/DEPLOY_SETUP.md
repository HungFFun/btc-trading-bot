# GitHub Actions CI/CD Setup

## 🚀 Tự động deploy lên Vultr khi push code

### 📋 **GitHub Secrets cần cấu hình:**

Truy cập: `https://github.com/HungFFun/btc-trading-bot/settings/secrets/actions`

Thêm các secrets sau:

| Secret Name | Description | Example |
|------------|-------------|---------|
| `VULTR_HOST` | IP address của Vultr server | `123.456.789.012` |
| `VULTR_USERNAME` | Username SSH (thường là `root`) | `root` |
| `VULTR_SSH_KEY` | Private SSH key để login | `-----BEGIN RSA PRIVATE KEY-----...` |
| `VULTR_SSH_PORT` | SSH port (mặc định 22) | `22` |
| `DEPLOY_PATH` | Đường dẫn project trên server | `/root/bot_featured` |

---

## 🔑 **Cách lấy SSH Private Key:**

### **Option 1: Sử dụng key hiện có**

```bash
# Trên máy local (Mac)
cat ~/.ssh/id_rsa
```

Copy toàn bộ nội dung (bao gồm cả `-----BEGIN RSA PRIVATE KEY-----` và `-----END RSA PRIVATE KEY-----`)

### **Option 2: Tạo key mới cho GitHub Actions**

```bash
# Tạo SSH key mới
ssh-keygen -t rsa -b 4096 -C "github-actions@deploy" -f ~/.ssh/github_actions_key -N ""

# Xem private key (paste vào GitHub Secrets)
cat ~/.ssh/github_actions_key

# Xem public key (thêm vào Vultr server)
cat ~/.ssh/github_actions_key.pub
```

**Thêm public key vào Vultr server:**

```bash
# SSH vào Vultr server
ssh root@your-vultr-ip

# Thêm public key vào authorized_keys
echo "your-public-key-here" >> ~/.ssh/authorized_keys

# Set permissions
chmod 600 ~/.ssh/authorized_keys
chmod 700 ~/.ssh
```

---

## 🛠️ **Setup từng bước:**

### **Bước 1: Thêm GitHub Secrets**

1. Truy cập: https://github.com/HungFFun/btc-trading-bot/settings/secrets/actions
2. Click **"New repository secret"**
3. Thêm từng secret theo bảng trên
4. Click **"Add secret"**

### **Bước 2: Verify SSH Connection**

Test SSH connection trước:

```bash
# Từ máy local
ssh -i ~/.ssh/id_rsa root@your-vultr-ip "echo 'Connection successful!'"
```

Nếu thành công → GitHub Actions sẽ hoạt động!

### **Bước 3: Test Deployment**

```bash
# Push một thay đổi nhỏ để test
cd /Users/doxuanhung/Desktop/BOT_BTC/bot_featured
echo "# Test CI/CD" >> README.md
git add README.md
git commit -m "test: CI/CD deployment"
git push origin main
```

### **Bước 4: Monitor Deployment**

1. Truy cập: https://github.com/HungFFun/btc-trading-bot/actions
2. Xem workflow "Deploy to Vultr" đang chạy
3. Click vào workflow để xem logs chi tiết

---

## ⚙️ **Workflow hoạt động như thế nào:**

### **Trigger:**
- ✅ Tự động khi `git push origin main`
- ✅ Thủ công từ GitHub Actions tab (workflow_dispatch)

### **Steps:**

1. **Checkout code** - Clone repo
2. **SSH to Vultr** - Kết nối đến server
3. **Pull latest code** - `git pull origin main`
4. **Pull Docker images** - Update images nếu có
5. **Restart services** - `docker-compose down && up -d --build`
6. **Verify deployment** - Check container status
7. **Show logs** - Display recent logs

### **Thời gian deploy:**
- Khoảng **2-3 phút** cho mỗi lần deploy
- Bao gồm: pull code, rebuild, restart containers

---

## 🔍 **Troubleshooting:**

### **Lỗi: "Permission denied (publickey)"**

**Nguyên nhân:** SSH key không đúng hoặc chưa được thêm vào server

**Giải pháp:**
1. Kiểm tra `VULTR_SSH_KEY` có đúng định dạng không
2. Verify public key đã được thêm vào server: `cat ~/.ssh/authorized_keys`
3. Test SSH manually: `ssh -i ~/.ssh/id_rsa root@your-server`

### **Lỗi: "fatal: not a git repository"**

**Nguyên nhân:** `DEPLOY_PATH` không đúng

**Giải pháp:**
1. SSH vào server: `ssh root@your-server`
2. Kiểm tra đường dẫn: `ls -la /root/bot_featured`
3. Cập nhật `DEPLOY_PATH` secret

### **Lỗi: "docker-compose: command not found"**

**Nguyên nhân:** Docker Compose chưa được cài đặt trên server

**Giải pháp:**
```bash
# SSH vào Vultr
ssh root@your-vultr-ip

# Cài Docker Compose
apt-get update
apt-get install docker-compose-plugin -y
```

### **Containers không start:**

**Kiểm tra logs:**
```bash
ssh root@your-server
cd /root/bot_featured
docker-compose logs -f
```

---

## 🎯 **Best Practices:**

### **1. Test trên branch khác trước:**

```bash
# Tạo test branch
git checkout -b test-deploy

# Push để test (không trigger deploy)
git push origin test-deploy

# Merge vào main sau khi test OK
git checkout main
git merge test-deploy
git push origin main  # ← Deploy tự động
```

### **2. Rollback nếu cần:**

```bash
# SSH vào server
ssh root@your-server
cd /root/bot_featured

# Rollback đến commit trước
git reset --hard HEAD~1
docker-compose restart
```

### **3. Monitor sau mỗi deploy:**

- Check GitHub Actions logs
- Check Docker logs: `docker-compose logs -f`
- Test commands: `/status`, `/health`

---

## 📊 **Deployment Status:**

Sau khi setup xong, bạn sẽ thấy:

✅ **GitHub Actions:**
- Workflow status badge
- Deployment history
- Automated logs

✅ **Vultr Server:**
- Auto-update khi push code
- Zero-downtime deployment
- Container health checks

✅ **Workflow:**
```
Push code → GitHub → SSH to Vultr → Pull & Restart → ✅ Done!
```

---

## 🎉 **Lợi ích:**

1. **Tự động hóa hoàn toàn** - Không cần SSH thủ công
2. **Fast deployment** - 2-3 phút mỗi lần
3. **Consistent** - Luôn deploy đúng cách
4. **Traceable** - Logs đầy đủ trên GitHub
5. **Safe** - Có thể rollback dễ dàng

---

**Created:** 2025-12-31  
**Status:** Ready to use  
**Next:** Add GitHub Secrets và test deployment!

