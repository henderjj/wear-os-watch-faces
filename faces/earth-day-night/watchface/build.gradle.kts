/*
 * Copyright 2024 The Android Open Source Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     https://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
plugins {
    alias(libs.plugins.android.application)
}

android {
    enableKotlin = false
    namespace = "uk.earthface.daynight"
    compileSdk = 33

    defaultConfig {
        applicationId = "uk.earthface.daynight"
        minSdk = 33
        targetSdk = 33
        versionCode = 5
        versionName = "1.2.2"
    }

    buildTypes {
        debug {
          isMinifyEnabled = true
        }
        release {
            // TODO:Add your signingConfig here to build release builds
            isMinifyEnabled = true
            // Ensure shrink resources is false, to avoid potential for them
            // being removed.
            isShrinkResources = false

            signingConfig = signingConfigs.getByName("debug")
        }
    }
}
