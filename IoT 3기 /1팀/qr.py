import qrcode

data = "105"  # QR코드에 담을 내용

qr = qrcode.make(data)
qr.save("105_qrcode.png")  # 101_qrcode.png 파일로 저장

print("QR 코드가 105_qrcode.png로 저장됐어!")
