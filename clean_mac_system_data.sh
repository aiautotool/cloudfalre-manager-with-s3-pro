#!/bin/bash

# Script dọn dẹp System Data và Cache trên macOS
# Tác giả: Antigravity Agent

# Màu sắc cho output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Bắt đầu dọn dẹp System Data trên Mac ===${NC}"
echo "Lưu ý: Script này sẽ xóa cache và file tạm. Hãy chắc chắn bạn đã sao lưu dữ liệu quan trọng."

# 1. Hiển thị dung lượng hiện tại
echo -e "\n${YELLOW}[1] Dung lượng đĩa hiện tại:${NC}"
df -h / | grep /

# 2. Xóa User Caches
echo -e "\n${YELLOW}[2] Đang xóa User Caches (~/Library/Caches)...${NC}"
# Chỉ xóa nội dung bên trong, giữ lại thư mục gốc
rm -rf ~/Library/Caches/*
echo "Đã xóa User Caches."

# 3. Xóa Logs
echo -e "\n${YELLOW}[3] Đang xóa Logs (~/Library/Logs)...${NC}"
rm -rf ~/Library/Logs/*
echo "Đã xóa Logs."

# 4. Xóa Xcode DerivedData (Dành cho Developer)
if [ -d "$HOME/Library/Developer/Xcode/DerivedData" ]; then
    echo -e "\n${YELLOW}[4] Đang xóa Xcode DerivedData...${NC}"
    rm -rf "$HOME/Library/Developer/Xcode/DerivedData/"*
    echo "Đã xóa Xcode DerivedData."
else
    echo -e "\n${YELLOW}[4] Không tìm thấy thư mục Xcode DerivedData. Bỏ qua.${NC}"
fi

# 5. Xóa iOS DeviceSupport cũ (Thường chiếm nhiều chỗ)
echo -e "\n${YELLOW}[5] Kiểm tra iOS Device Support (Thường rất nặng):${NC}"
if [ -d "$HOME/Library/Developer/Xcode/iOS DeviceSupport" ]; then
    # Liệt kê dung lượng
    du -sh "$HOME/Library/Developer/Xcode/iOS DeviceSupport/"* 2>/dev/null
    echo -e "${RED}Lưu ý: Thư mục này chứa file debug cho các phiên bản iOS cũ.${NC}"
    echo "Nếu bạn muốn xóa, hãy chạy lệnh thủ công: rm -rf ~/Library/Developer/Xcode/iOS\ DeviceSupport/*"
else
    echo "Không tìm thấy thư mục iOS DeviceSupport."
fi

# 6. Homebrew Cleanup
if command -v brew &> /dev/null; then
    echo -e "\n${YELLOW}[6] Đang chạy Homebrew Cleanup...${NC}"
    brew cleanup
else
    echo -e "\n${YELLOW}[6] Homebrew không được cài đặt. Bỏ qua.${NC}"
fi

# 7. Docker Cleanup (nếu có)
if command -v docker &> /dev/null; then
    echo -e "\n${YELLOW}[7] Kiểm tra Docker...${NC}"
    echo "Bạn có muốn chạy 'docker system prune' để xóa container/image không dùng? (y/n)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])+$ ]]; then
        docker system prune -f
    else
        echo "Bỏ qua Docker cleanup."
    fi
fi

# 8. Gợi ý kiểm tra Time Machine Snapshots (có thể chiếm nhiều System Data)
echo -e "\n${YELLOW}[8] Kiểm tra Local Time Machine Snapshots...${NC}"
echo "Các bản backup Time Machine cục bộ có thể chiếm nhiều dung lượng System Data."
echo "Danh sách snapshot hiện tại (cần quyền hệ thống, có thể yêu cầu mật khẩu nếu chạy tmutil):"
# tmutil listlocalsnapshots /
echo "Để xóa snapshot, bạn có thể dùng lệnh: 'tmutil listlocalsnapshots /' rồi 'sudo tmutil deletelocalsnapshots <dấu thời gian>'"

# 9. Tìm các file lớn trong ~/Library (Nơi System Data thường ẩn nấp)
echo -e "\n${YELLOW}[9] Tìm 10 thư mục lớn nhất trong ~/Library (Quá trình này có thể mất vài giây)...${NC}"
du -d 1 -h ~/Library/ 2>/dev/null | sort -h | tail -n 10

echo -e "\n${GREEN}=== Hoàn tất dọn dẹp ===${NC}"
df -h / | grep /
