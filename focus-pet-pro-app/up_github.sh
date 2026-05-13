#!/bin/bash
cd ..
echo "1. Đang khởi tạo Git và lưu toàn bộ mã nguồn..."
git init
git add .
git commit -m "Hoàn thiện Focus Pet Pro v1.0 (Bao gồm App Desktop và Chrome Extension)"
git branch -M main

echo "2. Đang kết nối với GitHub..."
if command -v gh &> /dev/null
then
    echo "Phát hiện GitHub CLI. Tiến hành tạo kho chứa tự động..."
    gh repo create focus-pet-pro --private --source=. --remote=origin --push
    echo "🎉 HOÀN TẤT! Toàn bộ mã nguồn đã được đẩy lên GitHub thành công (Chế độ Private)."
else
    echo "❌ Hệ thống chưa cài đặt GitHub CLI để tạo tự động."
    echo "Vui lòng truy cập trang web github.com, tạo một Repository trống (đặt tên là focus-pet-pro)."
    echo "Sau đó, copy đường link GitHub của bạn và chạy 2 lệnh sau trong Terminal:"
    echo "git remote add origin <ĐƯỜNG_LINK_GITHUB_CỦA_BẠN_Ở_ĐÂY>"
    echo "git push -u origin main"
fi
