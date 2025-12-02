package org.pytorch.demo.objectdetection;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AlertDialog;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;
import androidx.exifinterface.media.ExifInterface;
import androidx.core.content.FileProvider;

import android.Manifest;
import android.content.ContentResolver;
import android.content.ContentValues;
import android.content.Context;
import android.content.DialogInterface;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.ImageDecoder;
import android.graphics.Matrix;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.provider.MediaStore;
import android.util.Log;
import android.view.View;
import android.widget.Button;
import android.widget.ImageView;
import android.widget.ProgressBar;
import android.widget.Toast;

import org.pytorch.IValue;
import org.pytorch.LiteModuleLoader;
import org.pytorch.Module;
import org.pytorch.Tensor;
import org.pytorch.torchvision.TensorImageUtils;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.io.IOException;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;

public class MainActivity extends AppCompatActivity implements Runnable {

    private static final int REQ_TAKE_PICTURE = 100;
    private static final int REQ_PICK_IMAGE   = 101;

    private int mImageIndex = 0;
    private String[] mTestImages;

    private ImageView mImageView;
    private ResultView mResultView;
    private Button mButtonDetect;
    private ProgressBar mProgressBar;
    private Bitmap mBitmap = null;
    private Module mModule = null;
    private float mImgScaleX, mImgScaleY, mIvScaleX, mIvScaleY, mStartX, mStartY;

    // 촬영 이미지가 저장될 URI (카메라 인텐트의 EXTRA_OUTPUT 대상)
    private Uri mCaptureUri = null;

    public static String assetFilePath(Context context, String assetName) throws IOException {
        File file = new File(context.getFilesDir(), assetName);
        if (file.exists() && file.length() > 0) return file.getAbsolutePath();
        try (InputStream is = context.getAssets().open(assetName);
             OutputStream os = new FileOutputStream(file)) {
            byte[] buffer = new byte[4096];
            int read;
            while ((read = is.read(buffer)) != -1) os.write(buffer, 0, read);
            os.flush();
        }
        return file.getAbsolutePath();
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // 권한
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
                != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this, new String[]{Manifest.permission.CAMERA}, 1);
        }
        if (Build.VERSION.SDK_INT >= 33) {
            final String READ_MEDIA_IMAGES = "android.permission.READ_MEDIA_IMAGES";
            if (ContextCompat.checkSelfPermission(this, READ_MEDIA_IMAGES)
                    != PackageManager.PERMISSION_GRANTED) {
                ActivityCompat.requestPermissions(this, new String[]{READ_MEDIA_IMAGES}, 2);
            }
        } else {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.READ_EXTERNAL_STORAGE)
                    != PackageManager.PERMISSION_GRANTED) {
                ActivityCompat.requestPermissions(this,
                        new String[]{Manifest.permission.READ_EXTERNAL_STORAGE}, 3);
            }
            // API 28 이하에서 갤러리에 저장하려면 WRITE 권한 필요할 수 있음
            if (Build.VERSION.SDK_INT <= 28 &&
                    ContextCompat.checkSelfPermission(this, Manifest.permission.WRITE_EXTERNAL_STORAGE)
                            != PackageManager.PERMISSION_GRANTED) {
                ActivityCompat.requestPermissions(this,
                        new String[]{Manifest.permission.WRITE_EXTERNAL_STORAGE}, 4);
            }
        }

        setContentView(R.layout.activity_main);

        // 샘플 이미지 (assets/1.png ~ 11.png)
        final int NUM_ASSET_IMAGES = 11;
        mTestImages = new String[NUM_ASSET_IMAGES];
        for (int i = 0; i < NUM_ASSET_IMAGES; i++) mTestImages[i] = (i + 1) + ".png";

        try {
            mBitmap = BitmapFactory.decodeStream(getAssets().open(mTestImages[mImageIndex]));
        } catch (IOException e) {
            Log.e("OD", "assets open fail", e);
            finish();
        }

        mImageView   = findViewById(R.id.imageView);
        mResultView  = findViewById(R.id.resultView);
        mButtonDetect= findViewById(R.id.detectButton);
        mProgressBar = findViewById(R.id.progressBar);

        if (mBitmap != null) mImageView.setImageBitmap(mBitmap);
        mResultView.setVisibility(View.INVISIBLE);

        final Button buttonTest = findViewById(R.id.testButton);
        buttonTest.setText(String.format("Test Image %d/%d (%s)",
                mImageIndex + 1, mTestImages.length, mTestImages[mImageIndex]));
        buttonTest.setOnClickListener(v -> {
            mResultView.setVisibility(View.INVISIBLE);
            mImageIndex = (mImageIndex + 1) % mTestImages.length;
            String fname = mTestImages[mImageIndex];
            buttonTest.setText(String.format("Test Image %d/%d (%s)",
                    mImageIndex + 1, mTestImages.length, fname));
            try {
                mBitmap = BitmapFactory.decodeStream(getAssets().open(fname));
                mImageView.setImageBitmap(mBitmap);
            } catch (IOException e) {
                Log.e("OD", "assets open fail", e);
            }
        });

        final Button buttonSelect = findViewById(R.id.selectButton);
        buttonSelect.setOnClickListener(v -> {
            mResultView.setVisibility(View.INVISIBLE);
            final CharSequence[] options = {"Choose from Photos", "Take Picture", "Cancel"};
            new AlertDialog.Builder(MainActivity.this)
                    .setTitle("New Test Image")
                    .setItems(options, (DialogInterface dialog, int item) -> {
                        if (options[item].equals("Take Picture")) {
                            launchCameraAndSaveToGallery(); // 촬영→갤러리저장
                        } else if (options[item].equals("Choose from Photos")) {
                            Intent pick = new Intent(Intent.ACTION_PICK, MediaStore.Images.Media.EXTERNAL_CONTENT_URI);
                            startActivityForResult(pick, REQ_PICK_IMAGE);
                        } else dialog.dismiss();
                    }).show();
        });

        final Button buttonLive = findViewById(R.id.liveButton);
        buttonLive.setOnClickListener(v -> startActivity(new Intent(MainActivity.this, ObjectDetectionActivity.class)));

        mButtonDetect.setOnClickListener(v -> {
            if (mBitmap == null) {
                Toast.makeText(this, "이미지를 먼저 선택/촬영하세요.", Toast.LENGTH_SHORT).show();
                return;
            }
            mButtonDetect.setEnabled(false);
            mProgressBar.setVisibility(ProgressBar.VISIBLE);
            mButtonDetect.setText(getString(R.string.run_model));

            mImgScaleX = (float) mBitmap.getWidth() / PrePostProcessor.mInputWidth;
            mImgScaleY = (float) mBitmap.getHeight() / PrePostProcessor.mInputHeight;
            mIvScaleX  = (mBitmap.getWidth() > mBitmap.getHeight()
                    ? (float) mImageView.getWidth() / mBitmap.getWidth()
                    : (float) mImageView.getHeight() / mBitmap.getHeight());
            mIvScaleY  = (mBitmap.getHeight() > mBitmap.getWidth()
                    ? (float) mImageView.getHeight() / mBitmap.getHeight()
                    : (float) mImageView.getWidth() / mBitmap.getWidth());
            mStartX = (mImageView.getWidth() - mIvScaleX * mBitmap.getWidth()) / 2f;
            mStartY = (mImageView.getHeight() - mIvScaleY * mBitmap.getHeight()) / 2f;

            new Thread(MainActivity.this).start();
        });

        // 모델/라벨 로드
        try {
            mModule = LiteModuleLoader.load(
                    MainActivity.assetFilePath(getApplicationContext(), "model_v5n_320_20250904_082313.ptl")
            );
            BufferedReader br = new BufferedReader(new InputStreamReader(getAssets().open("classes.txt")));
            List<String> classes = new ArrayList<>();
            String line;
            while ((line = br.readLine()) != null) {
                if (!line.trim().isEmpty()) classes.add(line.trim());
            }
            if (classes.isEmpty()) classes.add("class0");
            PrePostProcessor.setClasses(classes.toArray(new String[0]));
        } catch (IOException e) {
            Log.e("OD", "model/labels load fail", e);
            Toast.makeText(this, "Model/labels load failed: " + e.getMessage(), Toast.LENGTH_LONG).show();
            finish();
        }
    }

    // 카메라 실행 + 저장할 Uri 준비 (API 29+ : MediaStore / 하위: FileProvider)
    private void launchCameraAndSaveToGallery() {
        Intent it = new Intent(MediaStore.ACTION_IMAGE_CAPTURE);

        try {
            if (Build.VERSION.SDK_INT >= 29) {
                mCaptureUri = createImageUriApi29Plus();
            } else {
                File f = createImageFileLegacy();
                mCaptureUri = FileProvider.getUriForFile(
                        this, getPackageName() + ".fileprovider", f);
            }
        } catch (Exception e) {
            Toast.makeText(this, "촬영용 파일 준비 실패: " + e.getMessage(), Toast.LENGTH_LONG).show();
            return;
        }

        if (mCaptureUri == null) {
            Toast.makeText(this, "저장 위치를 만들 수 없습니다.", Toast.LENGTH_SHORT).show();
            return;
        }

        it.putExtra(MediaStore.EXTRA_OUTPUT, mCaptureUri);
        it.addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION | Intent.FLAG_GRANT_READ_URI_PERMISSION);
        startActivityForResult(it, REQ_TAKE_PICTURE);
    }

    private Uri createImageUriApi29Plus() {
        ContentValues values = new ContentValues();
        String time = new SimpleDateFormat("yyyyMMdd_HHmmss").format(new Date());
        values.put(MediaStore.Images.Media.DISPLAY_NAME, "IMG_" + time + ".jpg");
        values.put(MediaStore.Images.Media.MIME_TYPE, "image/jpeg");
        values.put(MediaStore.Images.Media.RELATIVE_PATH, Environment.DIRECTORY_PICTURES + "/Camera");
        values.put(MediaStore.Images.Media.IS_PENDING, 0);
        return getContentResolver().insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values);
    }

    private File createImageFileLegacy() throws IOException {
        String time = new SimpleDateFormat("yyyyMMdd_HHmmss").format(new Date());
        String fileName = "IMG_" + time;
        File storageDir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_PICTURES);
        if (!storageDir.exists()) storageDir.mkdirs();
        return File.createTempFile(fileName, ".jpg", storageDir);
    }

    // 갤러리/카메라 결과 처리
    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (resultCode != RESULT_OK) {
            Toast.makeText(this, "취소되었습니다.", Toast.LENGTH_SHORT).show();
            return;
        }

        try {
            if (requestCode == REQ_TAKE_PICTURE) {
                if (mCaptureUri == null) {
                    Toast.makeText(this, "촬영 이미지 URI 누락", Toast.LENGTH_SHORT).show();
                    return;
                }
                mBitmap = loadBitmapFixOrientation(mCaptureUri);   // 회전보정 + ARGB_8888
                if (mBitmap == null) {
                    Toast.makeText(this, "촬영 이미지를 불러오지 못했습니다.", Toast.LENGTH_SHORT).show();
                    return;
                }
                mImageView.setImageBitmap(mBitmap);
                Toast.makeText(this, "갤러리에 저장 완료", Toast.LENGTH_SHORT).show();

            } else if (requestCode == REQ_PICK_IMAGE) {
                if (data == null || data.getData() == null) {
                    Toast.makeText(this, "갤러리에서 이미지를 가져오지 못했습니다.", Toast.LENGTH_SHORT).show();
                    return;
                }
                Uri uri = data.getData();
                mBitmap = loadBitmapFixOrientation(uri);           // 회전보정 + ARGB_8888
                if (mBitmap == null) {
                    Toast.makeText(this, "이미지 디코딩 실패", Toast.LENGTH_SHORT).show();
                    return;
                }
                mImageView.setImageBitmap(mBitmap);
            }

        } catch (Exception e) {
            Log.e("OD", "image load fail", e);
            Toast.makeText(this, "이미지 불러오기 실패: " + e.getMessage(), Toast.LENGTH_SHORT).show();
        }
    }

    /** 큰 이미지를 안전하게 다운샘플링해서 로드 */
    private Bitmap loadBitmapDownsampled(@NonNull Uri uri, int targetMax) throws IOException {
        BitmapFactory.Options opts = new BitmapFactory.Options();
        opts.inJustDecodeBounds = true;
        try (InputStream is = getContentResolver().openInputStream(uri)) {
            BitmapFactory.decodeStream(is, null, opts);
        }
        int w = opts.outWidth, h = opts.outHeight;
        if (w <= 0 || h <= 0) return loadBitmapFixOrientation(uri);

        int sample = 1;
        int maxDim = Math.max(w, h);
        while ((maxDim / sample) > targetMax) sample *= 2;

        opts = new BitmapFactory.Options();
        opts.inSampleSize = sample;
        opts.inPreferredConfig = Bitmap.Config.ARGB_8888;
        Bitmap bmp;
        try (InputStream is2 = getContentResolver().openInputStream(uri)) {
            bmp = BitmapFactory.decodeStream(is2, null, opts);
        }
        if (bmp == null) return null;

        int deg = getExifRotation(uri);
        if (deg != 0) {
            Matrix m = new Matrix();
            m.postRotate(deg);
            bmp = Bitmap.createBitmap(bmp, 0, 0, bmp.getWidth(), bmp.getHeight(), m, true);
        }

        if (bmp.getConfig() != Bitmap.Config.ARGB_8888) {
            bmp = bmp.copy(Bitmap.Config.ARGB_8888, false);
        }
        return bmp;
    }

    /** 갤러리/촬영 URI → Bitmap 디코드 + EXIF 각도만큼 회전 */
    private Bitmap loadBitmapFixOrientation(@NonNull Uri uri) throws IOException {
        Bitmap bmp;
        if (Build.VERSION.SDK_INT >= 28) {
            ImageDecoder.Source src = ImageDecoder.createSource(getContentResolver(), uri);
            bmp = ImageDecoder.decodeBitmap(src, (decoder, info, src2) -> {
                decoder.setAllocator(ImageDecoder.ALLOCATOR_SOFTWARE);
            });
        } else {
            BitmapFactory.Options opts = new BitmapFactory.Options();
            opts.inPreferredConfig = Bitmap.Config.ARGB_8888;
            try (InputStream is = getContentResolver().openInputStream(uri)) {
                bmp = BitmapFactory.decodeStream(is, null, opts);
            }
        }

        int deg = getExifRotation(uri);
        if (deg != 0 && bmp != null) {
            Matrix m = new Matrix();
            m.postRotate(deg);
            bmp = Bitmap.createBitmap(bmp, 0, 0, bmp.getWidth(), bmp.getHeight(), m, true);
        }

        if (bmp != null && bmp.getConfig() != Bitmap.Config.ARGB_8888) {
            bmp = bmp.copy(Bitmap.Config.ARGB_8888, false);
        }
        return bmp;
    }

    private int getExifRotation(@NonNull Uri uri) throws IOException {
        ExifInterface exif;
        if (ContentResolver.SCHEME_CONTENT.equals(uri.getScheme())) {
            try (InputStream is = getContentResolver().openInputStream(uri)) {
                exif = new ExifInterface(is);
            }
        } else {
            exif = new ExifInterface(uri.getPath());
        }
        int o = exif.getAttributeInt(ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL);
        switch (o) {
            case ExifInterface.ORIENTATION_ROTATE_90:  return 90;
            case ExifInterface.ORIENTATION_ROTATE_180: return 180;
            case ExifInterface.ORIENTATION_ROTATE_270: return 270;
            default: return 0;
        }
    }

    /** forward() 결과에서 첫 번째 Tensor를 안전하게 뽑는다 */
    private Tensor extractFirstTensor(IValue out) {
        if (out == null) return null;
        if (out.isTensor()) return out.toTensor();
        if (out.isTuple()) {
            IValue[] tup = out.toTuple();
            if (tup != null) {
                for (IValue v : tup) {
                    if (v != null && v.isTensor()) return v.toTensor();
                }
            }
        }
        if (out.isList()) {
            IValue[] arr = out.toList();
            if (arr != null) {
                for (IValue v : arr) {
                    if (v != null && v.isTensor()) return v.toTensor();
                }
            }
        }
        return null;
    }

    // 추론 스레드
    @Override
    public void run() {
        try {
            if (mBitmap == null || mModule == null) {
                runOnUiThread(() -> {
                    Toast.makeText(this, "이미지/모델이 비어있습니다.", Toast.LENGTH_SHORT).show();
                    mButtonDetect.setEnabled(true);
                    mProgressBar.setVisibility(ProgressBar.INVISIBLE);
                });
                return;
            }

            Bitmap resized = Bitmap.createScaledBitmap(
                    mBitmap, PrePostProcessor.mInputWidth, PrePostProcessor.mInputHeight, true);

            final Tensor inputTensor = TensorImageUtils.bitmapToFloat32Tensor(
                    resized, PrePostProcessor.NO_MEAN_RGB, PrePostProcessor.NO_STD_RGB);

            IValue iv = mModule.forward(IValue.from(inputTensor));
            Tensor outTensor = extractFirstTensor(iv);
            if (outTensor == null) {
                runOnUiThread(() -> {
                    Toast.makeText(this, "모델 출력에서 Tensor를 찾지 못했습니다.", Toast.LENGTH_LONG).show();
                    mButtonDetect.setEnabled(true);
                    mProgressBar.setVisibility(ProgressBar.INVISIBLE);
                });
                return;
            }

            final float[] outputs  = outTensor.getDataAsFloatArray();
            if (outputs == null || outputs.length == 0) {
                runOnUiThread(() -> {
                    Toast.makeText(this, "모델 출력이 비어있습니다.", Toast.LENGTH_LONG).show();
                    mButtonDetect.setEnabled(true);
                    mProgressBar.setVisibility(ProgressBar.INVISIBLE);
                });
                return;
            }

            final ArrayList<Result> results = PrePostProcessor.postprocessDynamic(
                    outputs, mImgScaleX, mImgScaleY, mIvScaleX, mIvScaleY, mStartX, mStartY);

            runOnUiThread(() -> {
                mButtonDetect.setEnabled(true);
                mButtonDetect.setText(getString(R.string.detect));
                mProgressBar.setVisibility(ProgressBar.INVISIBLE);
                if (results == null) {
                    Toast.makeText(this, "모델 출력 포맷을 해석할 수 없습니다.", Toast.LENGTH_LONG).show();
                    mResultView.setVisibility(View.INVISIBLE);
                } else {
                    mResultView.setResults(results);
                    mResultView.invalidate();
                    mResultView.setVisibility(View.VISIBLE);
                }
            });

        } catch (Throwable t) {
            Log.e("OD", "detect failed", t);
            runOnUiThread(() -> {
                Toast.makeText(this, "탐지 중 오류: " + t.getClass().getSimpleName()
                        + (t.getMessage() != null ? " - " + t.getMessage() : ""), Toast.LENGTH_LONG).show();
                mButtonDetect.setEnabled(true);
                mProgressBar.setVisibility(ProgressBar.INVISIBLE);
            });
        }
    }
}
