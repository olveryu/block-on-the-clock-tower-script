#!/bin/bash
# 百妖谱图片迁移脚本
# 从 bloodstar.clocktica.com 下载所有图片到本地，并生成新的 JSON

set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
IMG_DIR="$REPO_DIR/images"
JSON_IN="$REPO_DIR/yaoguai.json"
JSON_OUT="$REPO_DIR/yaoguai.json"

# GitHub raw URL base (上传后图片的访问地址)
GITHUB_RAW_BASE="https://raw.githubusercontent.com/olveryu/block-on-the-clock-tower-script/main/images"

# 旧 URL base
OLD_BASE="https://bloodstar.clocktica.com/p/olveryu/yaoguai"

echo "=== 百妖谱图片迁移工具 ==="
echo ""

# 1. 创建 images 目录
mkdir -p "$IMG_DIR"

# 2. 从 JSON 提取所有图片 URL 并下载
echo "📥 正在下载图片..."

# 提取所有 image 和 logo 字段的 URL
URLS=$(grep -oE 'https://bloodstar\.clocktica\.com/[^"]+\.(png|jpg|jpeg|gif|webp)' "$JSON_IN" | sort -u)

FAIL=0
SUCCESS=0

for url in $URLS; do
    filename=$(basename "$url")
    dest="$IMG_DIR/$filename"
    
    if [ -f "$dest" ]; then
        echo "  ✅ 已存在: $filename"
        SUCCESS=$((SUCCESS + 1))
        continue
    fi
    
    echo "  ⬇️  下载: $filename"
    if curl -sfL -o "$dest" "$url"; then
        # 检查文件大小，确保不是空文件
        if [ -s "$dest" ]; then
            echo "     ✅ 成功"
            SUCCESS=$((SUCCESS + 1))
        else
            echo "     ❌ 下载了空文件，删除"
            rm -f "$dest"
            FAIL=$((FAIL + 1))
        fi
    else
        echo "     ❌ 下载失败"
        FAIL=$((FAIL + 1))
    fi
done

echo ""
echo "📊 下载结果: 成功 $SUCCESS, 失败 $FAIL"

if [ $FAIL -gt 0 ]; then
    echo "⚠️  有 $FAIL 个文件下载失败，请检查后重试"
fi

# 3. 替换 JSON 中的 URL
echo ""
echo "📝 正在更新 JSON 中的图片链接..."

# 使用 sed 替换所有 bloodstar URL 为 GitHub raw URL
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS sed
    sed -i '' "s|$OLD_BASE/|$GITHUB_RAW_BASE/|g" "$JSON_OUT"
else
    # Linux sed
    sed -i "s|$OLD_BASE/|$GITHUB_RAW_BASE/|g" "$JSON_OUT"
fi

echo "✅ JSON 已更新!"
echo ""

# 4. 验证
echo "📋 验证: JSON 中是否还有旧链接..."
if grep -q "bloodstar.clocktica.com" "$JSON_OUT"; then
    echo "⚠️  仍有残留的 bloodstar 链接:"
    grep -o 'https://bloodstar[^"]*' "$JSON_OUT"
else
    echo "✅ 所有链接已替换为 GitHub 地址"
fi

echo ""
echo "=== 完成! ==="
echo ""
echo "下一步:"
echo "  cd $REPO_DIR"
echo "  git add ."
echo "  git commit -m 'feat: 迁移百妖谱图片至 GitHub'"
echo "  git push origin main"
echo ""
echo "推送后，你的新 JSON 文件可以直接导入 clocktower.online 使用。"
echo "almanac 链接 (bloodstar 的 HTML) 需要另外处理或移除。"
